from __future__ import annotations

from pathlib import Path

import pytest

from backend.storage.config import StorageConfig
from backend.storage.db import Database, IntegrityError, NotFoundError


def test_crud_with_single_quote_path(storage: StorageConfig) -> None:
    quoted = storage.db_path.parent / "O'Brien's folder"
    quoted.mkdir(parents=True)
    db = Database(storage.db_path, legacy_db_paths=[])
    try:
        mask_id = db.list_masks()[0].id
        record = db.create_folder(str(quoted), quoted.name, False, mask_id)
        assert record.original_path == str(quoted)

        results = db.list_folders(search="O'Brien")
        assert len(results) == 1

        updated = db.update_folder(record.id, display_name="renamed", hidden=True)
        assert updated.display_name == "renamed"
        assert updated.hidden is True

        db.delete_folder(record.id)
        with pytest.raises(NotFoundError):
            db.delete_folder(record.id)
    finally:
        db.close()


def test_path_column_is_text_not_varchar(storage: StorageConfig) -> None:
    long_name = "a" * 120
    long_path = storage.db_path.parent / long_name
    long_path.mkdir(parents=True)
    db = Database(storage.db_path, legacy_db_paths=[])
    try:
        record = db.create_folder(str(long_path), long_path.name, False, None)
        assert record.original_path == str(long_path)
        assert len(record.original_path) > 100
    finally:
        db.close()


def test_duplicate_original_path_rejected(storage: StorageConfig, tmp_path: Path) -> None:
    folder = tmp_path / "dup"
    folder.mkdir()
    db = Database(storage.db_path, legacy_db_paths=[])
    try:
        db.create_folder(str(folder), folder.name, False, None)
        with pytest.raises(IntegrityError):
            db.create_folder(str(folder), folder.name, False, None)
    finally:
        db.close()


def test_duplicate_windows_path_different_case_rejected(storage: StorageConfig) -> None:
    """Windows 大小写不敏感：C:\\Foo 与 C:\\foo 是同一目录，不能存两条。"""
    db = Database(storage.db_path, legacy_db_paths=[])
    try:
        db.create_folder("C:\\Foo", "Foo", False, None)
        with pytest.raises(IntegrityError):
            db.create_folder("C:\\foo", "foo", False, None)
        assert db.get_folder_by_original_path("c:\\FOO") is not None
    finally:
        db.close()


def test_legacy_migration_restores_eight_records(storage: StorageConfig, legacy_db: Path) -> None:
    db = Database(storage.db_path, legacy_db_paths=[legacy_db])
    try:
        folders = db.list_folders()
        assert len(folders) == 8
        paths = {f.original_path for f in folders}
        assert "F:/example-project" in paths
        assert "F:/example-archive" in paths
        assert "D:/.example-temp" in paths
        assert legacy_db.is_file()  # 旧文件保留，不删除
        recycle = next(f for f in folders if f.display_name == "example-project")
        assert recycle.mask_id is not None
        mask = db.get_mask(recycle.mask_id)
        assert mask is not None and mask.name == "回收站"
    finally:
        db.close()


def test_custom_mask_crud(storage: StorageConfig) -> None:
    db = Database(storage.db_path, legacy_db_paths=[])
    try:
        mask = db.create_custom_mask("新建文件夹", None)
        assert mask.clsid is None
        assert mask.builtin is False

        updated = db.update_custom_mask(mask.id, clsid="00021401-0000-0000-c000-000000000046")
        assert updated.clsid == "{00021401-0000-0000-C000-000000000046}"

        db.delete_custom_mask(mask.id)
        assert db.get_mask(mask.id) is None
    finally:
        db.close()
