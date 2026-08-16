"""pywebview 壳：窗口、原生目录选择框、WebView2 拖拽真实路径桥接（1-14 / 2-4）。"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import __version__  # noqa: E402
from backend.app import build_app  # noqa: E402


class ShellApi:
    """暴露给前端 ``window.pywebview.api`` 的方法。"""

    def __init__(self) -> None:
        self._window = None
        self._drop_registered = False

    def attach_window(self, window: Any) -> None:
        self._window = window

    def select_folder(self) -> dict[str, str]:
        """原生目录选择框，替代旧版 tkinter hack。"""
        window = self._window
        if window is None:
            return {"ok": False, "error": "window not ready"}
        import webview

        result = window.create_file_dialog(webview.FOLDER_DIALOG)
        path = result[0] if isinstance(result, (list, tuple)) and result else result
        if not path:
            return {"ok": False}
        return {"ok": True, "path": str(path), "folder": Path(path).name or str(path)}

    def register_drop_zone(self) -> bool:
        """前端挂载完成后调用；用 pywebview DOM 事件拿到 WebView2 的真实文件路径。"""
        window = self._window
        if window is None or self._drop_registered:
            return self._drop_registered
        try:
            window.events.loaded.wait(timeout=10)
            from webview.dom import DOMEventHandler

            drop_zone = window.dom.get_element("#drop-zone")
            if drop_zone is None:
                return False
            drop_zone.on(
                "drop",
                DOMEventHandler(
                    self._on_native_drop,
                    prevent_default=True,
                    stop_propagation=True,
                ),
            )
            self._drop_registered = True
        except Exception:
            # DOM 桥接是增强功能，失败时前端仍可手动选择。
            self._drop_registered = False
        return self._drop_registered

    def _on_native_drop(self, event: dict[str, Any]) -> None:
        files = (event.get("dataTransfer") or {}).get("files") or []
        paths: list[str] = []
        for file in files:
            path = file.get("pywebviewFullPath") or file.get("path") or file.get("fullPath")
            if path:
                paths.append(str(path))
        if not paths:
            return
        js = (
            "window.MaskBox && window.MaskBox.onNativeDrop && "
            f"window.MaskBox.onNativeDrop({json.dumps(paths)})"
        )
        try:
            self._window.evaluate_js(js)
        except Exception:
            logging.getLogger("maskbox.shell").exception("failed to forward native drop to JS")

    def app_version(self) -> str:
        return __version__


def main() -> None:
    import webview

    # Flask 绑 127.0.0.1 + 随机端口；server.url 才传给 webview。
    app, storage, server = build_app(program_dir=ROOT, resource_root=ROOT)
    server.start()

    api = ShellApi()
    window = webview.create_window(
        "MaskBox - 不只是隐藏，还能伪装 / Not just hide, but disguise",
        url=server.url,
        js_api=api,
        width=1200,
        height=780,
        min_size=(980, 640),
    )
    api.attach_window(window)

    webview.start(debug=os.environ.get("MASKBOX_DEBUG") == "1")
    server.shutdown()


if __name__ == "__main__":
    main()
