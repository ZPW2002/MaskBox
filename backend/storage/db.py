"""SQLite 仓库层（1-2 / 1-3 / 1-9 / 1-10）。

- 全部动态 SQL 参数化，禁止 f-string 拼值；
- 旧 ``data.db`` 自动迁移并保留旧文件；
- 字段使用 TEXT（不再有 varchar 截断问题）；
- 单连接 + RLock 保证 Flask 多线程下的串行访问。
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Iterable, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.core.mask_engine import BUILTIN_MASKS, MaskRegistry
from backend.storage.models import (
    DDL_FOLDERS,
    DDL_INDEX_FOLDERS_MASK,
    DDL_INDEX_FOLDERS_PATH,
    DDL_MASKS,
    SCHEMA_VERSION,
    FolderRecord,
    MaskRecord,
)

_UNSET = object()

log = logging.getLogger("maskbox.db")

LEGACY_MASK_CLSIDS = {mask.name: mask.clsid for mask in BUILTIN_MASKS}

_SORT_COLUMNS = {
    "name": "f.display_name COLLATE NOCASE",
    "path": "f.original_path COLLATE NOCASE",
    "created_at": "f.created_at",
    "updated_at": "f.updated_at",
    "status": "f.hidden DESC, f.mask_id IS NOT NULL DESC, f.original_path COLLATE NOCASE",
}
_DEFAULT_SORT = "f.created_at DESC, f.id DESC"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_mask(row: Sequence[Any]) -> MaskRecord:
    return MaskRecord(
        id=int(row[0]),
        name=str(row[1]),
        clsid=row[2],
        builtin=bool(row[3]),
        created_at=str(row[4]),
        updated_at=str(row[5]),
    )


def _row_to_folder(row: Sequence[Any]) -> FolderRecord:
    return FolderRecord(
        id=int(row[0]),
        original_path=str(row[1]),
        display_name=str(row[2]),
        hidden=bool(row[3]),
        mask_id=None if row[4] is None else int(row[4]),
        created_at=str(row[5]),
        updated_at=str(row[6]),
    )


class IntegrityError(RuntimeError):
    """数据库约束不满足（例如路径重复）。"""


class NotFoundError(LookupError):
    """记录不存在。"""


class Database:
    def __init__(self, db_path: str | Path, *, legacy_db_paths: Iterable[str | Path] = ()) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_db_paths = [Path(p) for p in legacy_db_paths]
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._create_schema()
        self._seed_builtin_masks()
        self._migrate_legacy_if_needed()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # schema
    # ------------------------------------------------------------------
    def _create_schema(self) -> None:
        with self._lock:
            self.conn.execute(DDL_MASKS)
            self.conn.execute(DDL_FOLDERS)
            self.conn.execute(DDL_INDEX_FOLDERS_MASK)
            self.conn.execute(DDL_INDEX_FOLDERS_PATH)
            self.conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
            self.conn.commit()

    def _seed_builtin_masks(self) -> None:
        with self._lock:
            now = utc_now()
            for spec in BUILTIN_MASKS:
                self.conn.execute(
                    "INSERT OR IGNORE INTO masks(name, clsid, builtin, created_at, updated_at)"
                    " VALUES (?, ?, 1, ?, ?)",
                    (spec.name, spec.clsid, now, now),
                )
            self.conn.commit()

    # ------------------------------------------------------------------
    # legacy migration
    # ------------------------------------------------------------------
    def _migrate_legacy_if_needed(self) -> None:
        count = self._scalar("SELECT COUNT(*) FROM folders")
        if count:
            return
        for legacy in self.legacy_db_paths:
            if not legacy.is_file():
                continue
            if legacy.resolve() == self.db_path.resolve():
                continue
            migrated = self.migrate_legacy(legacy)
            log.info("migrated %s rows from %s", migrated, legacy)
            if migrated:
                break

    def migrate_legacy(self, legacy_path: str | Path) -> int:
        """把旧版单表 ``data(path, folder, hide, mask)`` 迁移到新 schema。"""
        source = Path(legacy_path)
        if not source.is_file():
            return 0

        with self._lock, closing(sqlite3.connect(source)) as legacy_conn:
            legacy_conn.row_factory = sqlite3.Row
            rows = legacy_conn.execute("SELECT path, folder, hide, mask FROM data").fetchall()

        migrated = 0
        for row in rows:
            mask_name = str(row["mask"]).strip()
            clsid = LEGACY_MASK_CLSIDS.get(mask_name)
            original_path = MaskRegistry.restore_original_path(
                str(row["path"]), mask_name if mask_name != "无" else "", clsid
            )
            if not original_path:
                continue
            display_name = str(row["folder"]).strip() or Path(original_path).name
            hidden = str(row["hide"]) == "是"
            mask_id = (
                self.get_mask_id_by_name(mask_name) if mask_name and mask_name != "无" else None
            )
            if mask_id is None and mask_name and mask_name != "无":
                mask_id = self.create_custom_mask(mask_name, clsid).id
            try:
                self.create_folder(original_path, display_name, hidden, mask_id)
                migrated += 1
            except IntegrityError:
                log.warning("skip duplicate legacy path: %s", original_path)
        return migrated

    # ------------------------------------------------------------------
    # generic helpers
    # ------------------------------------------------------------------
    def _scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        with self._lock:
            row = self.conn.execute(sql, params).fetchone()
            return row[0] if row is not None else None

    @staticmethod
    def _escape_like(term: str) -> str:
        return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # ------------------------------------------------------------------
    # masks
    # ------------------------------------------------------------------
    def list_masks(self) -> list[MaskRecord]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, name, clsid, builtin, created_at, updated_at FROM masks"
                " ORDER BY builtin DESC, name COLLATE NOCASE"
            ).fetchall()
        return [_row_to_mask(row) for row in rows]

    def get_mask(self, mask_id: int) -> MaskRecord | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT id, name, clsid, builtin, created_at, updated_at FROM masks WHERE id = ?",
                (mask_id,),
            ).fetchone()
        return _row_to_mask(row) if row else None

    def get_mask_id_by_name(self, name: str) -> int | None:
        with self._lock:
            row = self.conn.execute("SELECT id FROM masks WHERE name = ?", (name,)).fetchone()
        return int(row[0]) if row else None

    def _mask_name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        with self._lock:
            if exclude_id is None:
                row = self.conn.execute("SELECT 1 FROM masks WHERE name = ?", (name,)).fetchone()
            else:
                row = self.conn.execute(
                    "SELECT 1 FROM masks WHERE name = ? AND id != ?", (name, exclude_id)
                ).fetchone()
        return row is not None

    def create_custom_mask(self, name: str, clsid: str | None) -> MaskRecord:
        clean_name = MaskRegistry.validate_name(name)
        normalized = MaskRegistry.validate_clsid(clsid, allow_empty=True)
        if self._mask_name_exists(clean_name):
            raise IntegrityError(f"面具已存在: {clean_name} / Mask already exists: {clean_name}")
        now = utc_now()
        with self._lock:
            cursor = self.conn.execute(
                "INSERT INTO masks(name, clsid, builtin, created_at, updated_at)"
                " VALUES (?, ?, 0, ?, ?)",
                (clean_name, normalized, now, now),
            )
            self.conn.commit()
            mask_id = int(cursor.lastrowid)
        record = self.get_mask(mask_id)
        if record is None:  # pragma: no cover - defensive
            raise RuntimeError("created mask disappeared")
        return record

    def update_custom_mask(
        self, mask_id: int, *, name: str | None = None, clsid: str | None = None
    ) -> MaskRecord:
        record = self.get_mask(mask_id)
        if record is None:
            raise NotFoundError(f"面具不存在 / Mask not found: {mask_id}")
        if record.builtin:
            raise IntegrityError("内置面具不可修改 / Built-in masks cannot be modified")

        new_name = MaskRegistry.validate_name(name if name is not None else record.name)
        new_clsid = MaskRegistry.validate_clsid(
            clsid if clsid is not None else record.clsid, allow_empty=True
        )
        if self._mask_name_exists(new_name, exclude_id=mask_id):
            raise IntegrityError(f"面具已存在: {new_name} / Mask already exists: {new_name}")

        with self._lock:
            self.conn.execute(
                "UPDATE masks SET name = ?, clsid = ?, updated_at = ? WHERE id = ?",
                (new_name, new_clsid, utc_now(), mask_id),
            )
            self.conn.commit()
        updated = self.get_mask(mask_id)
        if updated is None:  # pragma: no cover
            raise NotFoundError(f"面具不存在 / Mask not found: {mask_id}")
        return updated

    def count_folders_using_mask(self, mask_id: int) -> int:
        return int(self._scalar("SELECT COUNT(*) FROM folders WHERE mask_id = ?", (mask_id,)) or 0)

    def delete_custom_mask(self, mask_id: int) -> None:
        record = self.get_mask(mask_id)
        if record is None:
            raise NotFoundError(f"面具不存在 / Mask not found: {mask_id}")
        if record.builtin:
            raise IntegrityError("内置面具不可删除 / Built-in masks cannot be deleted")
        if self.count_folders_using_mask(mask_id) > 0:
            raise IntegrityError("面具使用中，不能删除 / Mask is in use and cannot be deleted")
        with self._lock:
            self.conn.execute("DELETE FROM masks WHERE id = ?", (mask_id,))
            self.conn.commit()

    # ------------------------------------------------------------------
    # folders
    # ------------------------------------------------------------------
    def list_folders(self, *, search: str = "", sort: str = "created_at") -> list[FolderRecord]:
        sort_column = _SORT_COLUMNS.get(sort, _DEFAULT_SORT)
        sql = (
            "SELECT f.id, f.original_path, f.display_name, f.hidden, f.mask_id,"
            " f.created_at, f.updated_at FROM folders f"
        )
        params: Sequence[Any] = ()
        if search:
            like = f"%{self._escape_like(search)}%"
            sql += (
                " WHERE (f.original_path LIKE ? ESCAPE '\\' OR f.display_name LIKE ? ESCAPE '\\')"
            )
            params = (like, like)
        sql += " ORDER BY " + sort_column
        with self._lock:
            rows = self.conn.execute(sql, params).fetchall()
        return [_row_to_folder(row) for row in rows]

    def get_folder(self, folder_id: int) -> FolderRecord | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT id, original_path, display_name, hidden, mask_id, created_at, updated_at"
                " FROM folders WHERE id = ?",
                (folder_id,),
            ).fetchone()
        return _row_to_folder(row) if row else None

    def get_folder_by_original_path(self, original_path: str) -> FolderRecord | None:
        # Windows 文件系统大小写不敏感，同一目录不同大小写必须命中同一条记录。
        with self._lock:
            row = self.conn.execute(
                "SELECT id, original_path, display_name, hidden, mask_id, created_at, updated_at"
                " FROM folders WHERE original_path = ? COLLATE NOCASE",
                (original_path,),
            ).fetchone()
        return _row_to_folder(row) if row else None

    def create_folder(
        self,
        original_path: str,
        display_name: str,
        hidden: bool,
        mask_id: int | None,
    ) -> FolderRecord:
        if self.get_folder_by_original_path(original_path) is not None:
            raise IntegrityError("目录已存在 / Folder already exists")
        if mask_id is not None and self.get_mask(mask_id) is None:
            raise IntegrityError("面具不存在 / Mask does not exist")
        now = utc_now()
        with self._lock:
            cursor = self.conn.execute(
                "INSERT INTO folders(original_path, display_name, hidden, mask_id,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (original_path, display_name, int(bool(hidden)), mask_id, now, now),
            )
            self.conn.commit()
            folder_id = int(cursor.lastrowid)
        record = self.get_folder(folder_id)
        if record is None:  # pragma: no cover
            raise RuntimeError("created folder disappeared")
        return record

    def update_folder(
        self,
        folder_id: int,
        *,
        original_path: str | None = None,
        display_name: str | None = None,
        hidden: bool | None = None,
        mask_id: int | None | object = _UNSET,
    ) -> FolderRecord:
        record = self.get_folder(folder_id)
        if record is None:
            raise NotFoundError(f"记录不存在 / Folder not found: {folder_id}")

        new_path = original_path if original_path is not None else record.original_path
        if new_path != record.original_path:
            if self.get_folder_by_original_path(new_path) is not None:
                raise IntegrityError("目录已存在 / Folder already exists")
        new_mask_id = record.mask_id if mask_id is _UNSET else mask_id
        if new_mask_id is not None and self.get_mask(new_mask_id) is None:
            raise IntegrityError("面具不存在 / Mask does not exist")

        now = utc_now()
        with self._lock:
            self.conn.execute(
                "UPDATE folders SET original_path = ?, display_name = ?, hidden = ?,"
                " mask_id = ?, updated_at = ? WHERE id = ?",
                (
                    new_path,
                    display_name if display_name is not None else record.display_name,
                    int(record.hidden if hidden is None else bool(hidden)),
                    new_mask_id,
                    now,
                    folder_id,
                ),
            )
            self.conn.commit()
        updated = self.get_folder(folder_id)
        if updated is None:  # pragma: no cover
            raise NotFoundError(f"记录不存在 / Folder not found: {folder_id}")
        return updated

    def set_folder_hidden(self, folder_id: int, hidden: bool) -> FolderRecord:
        return self.update_folder(folder_id, hidden=hidden)

    def delete_folder(self, folder_id: int) -> None:
        record = self.get_folder(folder_id)
        if record is None:
            raise NotFoundError(f"记录不存在 / Folder not found: {folder_id}")
        with self._lock:
            self.conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            self.conn.commit()


def folder_to_dict(record: FolderRecord, mask: MaskRecord | None) -> dict[str, Any]:
    """序列化目录记录；``missing`` 的最终判定由 API 层根据真实物理路径覆盖。"""
    return {
        "id": record.id,
        "path": record.original_path,
        "display_name": record.display_name,
        "hidden": record.hidden,
        "mask": mask.to_dict() if mask else None,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "missing": not Path(record.original_path).exists(),
    }
