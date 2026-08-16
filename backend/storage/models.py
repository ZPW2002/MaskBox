"""数据模型与建表 DDL（1-10）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MaskRecord:
    id: int | None
    name: str
    clsid: str | None
    builtin: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "clsid": self.clsid,
            "builtin": self.builtin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class FolderRecord:
    id: int | None
    original_path: str
    display_name: str
    hidden: bool
    mask_id: int | None
    created_at: str
    updated_at: str


SCHEMA_VERSION = 2

DDL_MASKS = """
CREATE TABLE IF NOT EXISTS masks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL COLLATE NOCASE UNIQUE,
    clsid       TEXT,
    builtin     INTEGER NOT NULL DEFAULT 0 CHECK (builtin IN (0, 1)),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""

DDL_FOLDERS = """
CREATE TABLE IF NOT EXISTS folders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    hidden        INTEGER NOT NULL DEFAULT 0 CHECK (hidden IN (0, 1)),
    mask_id       INTEGER REFERENCES masks(id) ON DELETE SET NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
)
"""

DDL_INDEX_FOLDERS_MASK = "CREATE INDEX IF NOT EXISTS idx_folders_mask_id ON folders(mask_id)"
DDL_INDEX_FOLDERS_PATH = "CREATE INDEX IF NOT EXISTS idx_folders_path ON folders(original_path)"
