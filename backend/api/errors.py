"""统一错误处理（1-12）：对外只返回 {code,msg,data}，traceback 只进日志。"""

from __future__ import annotations

import logging
from typing import Any

from flask import jsonify, request

from backend.api.i18n import negotiate_locale, translate

log = logging.getLogger("maskbox.api")


class ApiError(Exception):
    def __init__(
        self,
        code: int,
        message_key: str,
        *,
        data: Any = None,
        status_code: int | None = None,
        message_values: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_key)
        self.code = code
        self.message_key = message_key
        self.data = data
        self.status_code = status_code if status_code is not None else code
        self.message_values = message_values or {}

    def body(self, locale: str) -> dict[str, Any]:
        return {
            "code": self.code,
            "msg": translate(self.message_key, locale, **self.message_values),
            "data": self.data,
        }


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        locale = negotiate_locale(request.args, request.headers)
        return jsonify(error.body(locale)), error.status_code

    @app.errorhandler(404)
    def handle_not_found(_error):
        locale = negotiate_locale(request.args, request.headers)
        return (
            jsonify({"code": 404, "msg": translate("error.not_found", locale), "data": None}),
            404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        locale = negotiate_locale(request.args, request.headers)
        return (
            jsonify(
                {"code": 405, "msg": translate("error.method_not_allowed", locale), "data": None}
            ),
            405,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        # 原始 traceback 只进日志，绝不进 HTTP 响应（隐私红线 + 1-12）。
        log.exception("unhandled API error: %s", error)
        locale = negotiate_locale(request.args, request.headers)
        if hasattr(request, "path") and request.path.startswith("/api/"):
            return (
                jsonify({"code": 500, "msg": translate("error.internal", locale), "data": None}),
                500,
            )
        # 非 API 页面（例如静态资源）按 Flask 默认处理。
        raise error
