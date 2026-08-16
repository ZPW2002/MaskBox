"""组装入口：headless 可用（不 import pywebview）。"""

from __future__ import annotations

import threading
from pathlib import Path

from flask import Flask
from werkzeug.serving import make_server

from backend import __version__
from backend.api import create_app
from backend.core.guard import Guard
from backend.core.hide_service import HideService
from backend.logging_setup import setup_logging
from backend.storage.config import StorageConfig
from backend.storage.db import Database


class ServerThread(threading.Thread):
    def __init__(self, app: Flask, host: str = "127.0.0.1", port: int = 0) -> None:
        super().__init__(name="maskbox-flask", daemon=True)
        self._server = make_server(host, port, app, threaded=True)
        self._started = threading.Event()
        self.host = host
        self.port = self._server.server_port
        self.url = f"http://{host}:{self._server.server_port}"

    def run(self) -> None:
        self._started.set()
        self._server.serve_forever()

    def shutdown(self) -> None:
        if self._started.is_set():
            self._server.shutdown()
            self.join(timeout=3)
        self._server.server_close()


def build_app(
    *,
    program_dir: str | Path | None = None,
    resource_root: str | Path | None = None,
    database: Database | None = None,
    hide_service: HideService | None = None,
    guard: Guard | None = None,
) -> tuple[Flask, StorageConfig, ServerThread]:
    """构建 Flask app 与 127.0.0.1 随机端口服务器。"""
    storage = StorageConfig.resolve(program_dir=program_dir, resource_root=resource_root)
    storage.ensure_dirs()
    setup_logging(storage.log_dir)
    app = create_app(storage, database=database, hide_service=hide_service, guard=guard)
    server = ServerThread(app, host="127.0.0.1", port=0)
    return app, storage, server


def run_headless() -> None:
    """命令行 headless 模式：便于测试 API 和未来换壳。"""
    app, storage, server = build_app()
    print(f"MaskBox {__version__} API listening on {server.url}", flush=True)
    print(f"database: {storage.db_path}", flush=True)
    server.run()


if __name__ == "__main__":
    run_headless()
