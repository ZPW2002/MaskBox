"""attrib 隐藏/恢复服务（S1 之外的系统调用封装）。

仅使用 argv 数组调用 ``attrib``，不经过 shell，路径中的引号、空格、特殊字符
都不会被解释。测试时可注入 ``runner`` mock；Linux CI 上默认 no-op。
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

log = logging.getLogger("maskbox.hide")

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class HideError(RuntimeError):
    """attrib 调用失败。"""


def _windows_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
    )


def _non_windows_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Linux/CI 上没有 attrib，保持 API 与测试可用。"""
    log.debug("skip attrib on non-Windows: %s", " ".join(args))
    return subprocess.CompletedProcess(list(args), 0, "", "")


class HideService:
    def __init__(self, runner: Runner | None = None) -> None:
        if runner is not None:
            self._runner = runner
        elif os.name == "nt":
            self._runner = _windows_runner
        else:
            self._runner = _non_windows_runner

    def set_hidden(self, path: str | Path, hidden: bool) -> None:
        folder = Path(path)
        flags = ("+s", "+h") if hidden else ("-s", "-h")
        result = self._runner(("attrib", os.fspath(folder), *flags))
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"attrib exited with {result.returncode}"
            raise HideError(f"设置属性失败: {detail} / Failed to set attributes: {detail}")

    def hide(self, path: str | Path) -> None:
        self.set_hidden(path, True)

    def unhide(self, path: str | Path) -> None:
        self.set_hidden(path, False)
