from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from backend.api import create_app
from backend.core.guard import Guard
from backend.core.hide_service import HideService
from backend.storage.config import StorageConfig
from backend.storage.db import Database


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StorageConfig:
    data_dir = tmp_path / "appdata" / "MaskBox"
    log_dir = tmp_path / "localappdata" / "MaskBox" / "logs"
    data_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)
    return StorageConfig.resolve(
        program_dir=tmp_path / "program",
        resource_root=tmp_path / "resources",
        env={"MASKBOX_DATA_DIR": str(data_dir), "MASKBOX_LOG_DIR": str(log_dir)},
    )


@pytest.fixture
def db(storage: StorageConfig) -> Database:
    database = Database(storage.db_path, legacy_db_paths=storage.legacy_db_paths)
    yield database
    database.close()


@pytest.fixture
def client(storage: StorageConfig, db: Database):
    app = create_app(storage, database=db, hide_service=HideService(), guard=Guard())
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def legacy_db(tmp_path: Path) -> Path:
    """构造旧版 data.db，包含 8 条旧格式数据。"""
    legacy = tmp_path / "python-flask" / "data" / "data.db"
    legacy.parent.mkdir(parents=True)
    conn = sqlite3.connect(legacy)
    conn.execute(
        "CREATE TABLE data(path varchar(100), folder varchar(50),"
        " hide varchar(10), mask varchar(50))"
    )
    rows = [
        (
            "F:/example-project.{645FF040-5081-101B-9F08-00AA002F954E}",
            "example-project",
            "否",
            "回收站",
        ),
        (
            "F:/example-archive.{00021401-0000-0000-C000-000000000046}",
            "example-archive",
            "否",
            "无关联文件",
        ),
        ("D:/.example-temp", ".example-temp", "是", "无"),
        ("D:/example-downloads", "example-downloads", "是", "无"),
        ("D:/example-drivers", "example-drivers", "是", "无"),
        ("D:/example-moved", "example-moved", "否", "无"),
        ("E:/example-data/example-app", "example-app", "否", "无"),
        ("E:/example-one", "example-one", "否", "无"),
    ]
    conn.executemany("INSERT INTO data VALUES (?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return legacy
