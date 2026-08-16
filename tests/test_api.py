from __future__ import annotations

from pathlib import Path

from backend.app import build_app


def _create_dir(root: Path, name: str) -> Path:
    folder = root / name
    folder.mkdir()
    return folder


def test_health_and_bind_loopback() -> None:
    app, storage, server = build_app()
    try:
        assert server.host == "127.0.0.1"
        assert server.port > 0
        assert server.url.startswith("http://127.0.0.1:")
    finally:
        server.shutdown()


def test_folder_crud_with_single_quote_path(client, tmp_path: Path) -> None:
    folder = _create_dir(tmp_path, "O'Brien's folder")
    r = client.post(
        "/api/folders",
        json={"path": str(folder), "hidden": False, "mask_id": None},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["code"] == 200
    folder_id = body["data"]["id"]

    r = client.get("/api/folders?search=O%27Brien&sort=name")
    assert r.status_code == 200
    assert len(r.get_json()["data"]) == 1

    r = client.patch(f"/api/folders/{folder_id}", json={"display_name": "renamed"})
    assert r.status_code == 200
    assert r.get_json()["data"]["display_name"] == "renamed"

    r = client.post(f"/api/folders/{folder_id}/toggle-hide", json={})
    assert r.status_code == 200
    assert r.get_json()["data"]["hidden"] is True

    r = client.delete(f"/api/folders/{folder_id}")
    assert r.status_code == 200
    assert r.get_json()["code"] == 200


def test_add_with_custom_mask_and_restore(client, tmp_path: Path) -> None:
    folder = _create_dir(tmp_path, "private")
    r = client.post("/api/masks", json={"name": "新建文件夹", "clsid": ""})
    assert r.status_code == 200
    mask_id = r.get_json()["data"]["id"]

    r = client.post("/api/folders", json={"path": str(folder), "mask_id": mask_id})
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["path"] == str(folder)
    assert data["current_path"] == str(tmp_path / "新建文件夹")
    assert not folder.exists()

    # 再次 PATCH 同名面具应幂等，不叠加。
    r = client.patch(f"/api/folders/{data['id']}", json={"mask_id": mask_id})
    assert r.status_code == 200
    assert r.get_json()["data"]["current_path"] == str(tmp_path / "新建文件夹")

    r = client.delete(f"/api/folders/{data['id']}")
    assert r.status_code == 200
    assert folder.exists()


def test_error_has_no_traceback(client) -> None:
    r = client.post("/api/folders", json={"path": "/no/such/path"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["code"] == 400
    assert "Traceback" not in body["msg"]
    assert "traceback" not in r.get_data(as_text=True).lower()


def test_guard_blocks_system_path(client) -> None:
    r = client.post("/api/folders", json={"path": "C:\\Windows\\System32"})
    assert r.status_code == 403
    assert r.get_json()["code"] == 403


def test_english_locale(client, tmp_path: Path) -> None:
    folder = _create_dir(tmp_path, "en")
    r = client.post(
        "/api/folders?lang=en",
        json={"path": str(folder), "hidden": False, "mask_id": None},
    )
    assert r.status_code == 200
    assert r.get_json()["msg"] == "Folder added"


def test_db_failure_rolls_back_folder_rename(client, tmp_path: Path, monkeypatch) -> None:
    folder = _create_dir(tmp_path, "rollback")
    r = client.post("/api/masks", json={"name": "测试面具", "clsid": ""})
    mask_id = r.get_json()["data"]["id"]

    from flask import current_app

    captured = {}

    def boom(*args, **kwargs):
        captured["called"] = True
        raise RuntimeError("db exploded")

    with client.application.app_context():
        db = current_app.extensions["maskbox_db"]

    monkeypatch.setattr(db, "create_folder", boom)
    r = client.post(
        "/api/folders",
        json={"path": str(folder), "mask_id": mask_id, "hidden": True},
    )
    assert r.status_code == 500
    assert captured.get("called") is True
    assert folder.exists()  # rename 已回滚
    assert (tmp_path / "测试面具").exists() is False


def test_legacy_migration_is_used_by_app(storage, legacy_db, tmp_path: Path) -> None:
    from backend.api import create_app
    from backend.core.guard import Guard
    from backend.core.hide_service import HideService
    from backend.storage.db import Database

    db = Database(storage.db_path, legacy_db_paths=[legacy_db])
    app = create_app(storage, database=db, hide_service=HideService(), guard=Guard())
    app.config["TESTING"] = True
    with app.test_client() as client:
        r = client.get("/api/folders")
        assert r.status_code == 200
        assert len(r.get_json()["data"]) == 8
    db.close()
