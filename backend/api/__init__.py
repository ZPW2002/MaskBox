"""Flask API 工厂。仅绑定 127.0.0.1，前端静态资源由 ``frontend/dist`` 提供。"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, send_from_directory

from backend.api.errors import register_error_handlers
from backend.api.routes import api_bp
from backend.core.guard import Guard
from backend.core.hide_service import HideService
from backend.storage.config import StorageConfig
from backend.storage.db import Database


def create_app(
    storage: StorageConfig,
    *,
    database: Database | None = None,
    hide_service: HideService | None = None,
    guard: Guard | None = None,
) -> Flask:
    # Flask 的 root_path 是 backend/api；前端 dist 必须使用绝对路径，否则会拼错。
    dist = storage.frontend_dist.resolve()
    app = Flask(
        __name__,
        static_folder=str(dist),
        static_url_path="/static",
    )
    app.config["MASKBOX_STORAGE"] = storage
    app.extensions["maskbox_db"] = database or Database(
        storage.db_path, legacy_db_paths=storage.legacy_db_paths
    )
    app.extensions["maskbox_hide_service"] = hide_service or HideService()
    app.extensions["maskbox_guard"] = guard or Guard()
    app.register_blueprint(api_bp)
    register_error_handlers(app)

    @app.get("/")
    def index():
        index_file = dist / "index.html"
        if index_file.is_file():
            return send_from_directory(dist, "index.html")
        return (
            "<h1>MaskBox</h1><p>Frontend not built. Run <code>npm run build</code> "
            "in <code>frontend/</code> or use the API under <code>/api/</code>.</p>",
            200,
        )

    @app.get("/<path:filename>")
    def spa_fallback(filename: str):
        # /api/ 未命中路由时交给统一 404 JSON。
        if filename.startswith("api/"):
            from flask import abort

            abort(404)
        target = (dist / filename).resolve()
        if target.is_file() and _is_relative_to(target, dist.resolve()):
            return send_from_directory(dist, filename)
        if "." not in Path(filename).name:
            index_file = dist / "index.html"
            if index_file.is_file():
                return send_from_directory(dist, "index.html")
        from flask import abort

        abort(404)

    return app


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
