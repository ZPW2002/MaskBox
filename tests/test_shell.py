from __future__ import annotations

import sys
from pathlib import Path

import pytest

from shell.main import build_shell_app


def test_shell_uses_bundled_frontend_dist_when_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PyInstaller 冻结后，前端必须解析到 ``sys._MEIPASS/frontend/dist``。

    曾经误把 ``resource_root=ROOT`` 传进去，而冻结后的 ROOT 是 exe 目录，
    导致发布包出现 "Frontend not built" 的降级页。
    """
    meipass = tmp_path / "_internal"
    dist = meipass / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>bundled</title>", encoding="utf-8")

    program = tmp_path / "MaskBox"
    program.mkdir()
    fake_exe = program / "MaskBox.exe"
    fake_exe.touch()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)
    monkeypatch.setenv("MASKBOX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MASKBOX_LOG_DIR", str(tmp_path / "logs"))

    app, storage, server = build_shell_app()
    try:
        assert storage.frontend_dist == dist
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert "bundled" in response.get_data(as_text=True)
    finally:
        server.shutdown()
