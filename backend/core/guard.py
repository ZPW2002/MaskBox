"""防呆守卫（1-7）。

黑名单只针对「一旦隐藏/伪装会让用户把自己系统搞坏」的路径：
盘符根、Windows、Program Files*、系统卷关键目录；正在运行的程序目录做
尽力检测并返回 ``confirmation``，由 UI 二次确认（API 的 ``force=true``）。
"""

from __future__ import annotations

import ntpath
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath

SYSTEM_COMPONENTS = ("windows",)
PROGRAM_FILES_PREFIX = "program files"
SYSTEM_VOLUME_COMPONENTS = (
    "$recycle.bin",
    "system volume information",
    "recovery",
    "config.msi",
    "documents and settings",
    "boot",
    "efi",
)


@dataclass(frozen=True, slots=True)
class GuardIssue:
    reason: str
    path: str
    message: str | None = None


@dataclass(slots=True)
class GuardResult:
    blocked: list[GuardIssue] = field(default_factory=list)
    confirmations: list[GuardIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blocked

    def to_dict(self) -> dict:
        def issue_to_dict(issue: GuardIssue) -> dict:
            return {"reason": issue.reason, "path": issue.path, "message": issue.message}

        return {
            "blocked": [issue_to_dict(issue) for issue in self.blocked],
            "confirmations": [issue_to_dict(issue) for issue in self.confirmations],
        }


def _is_windows_style_path(value: str) -> bool:
    return bool(ntpath.splitdrive(value)[0]) or value.startswith(("\\\\", "//"))


def _windows_parts(value: str) -> tuple[str, ...]:
    """用 Windows 语义拆路径；盘符不参与大小写敏感比较。"""
    return tuple(part.casefold() for part in PureWindowsPath(value).parts if part not in ("", "\\"))


def _path_contains(path: str, child: str) -> bool:
    """判断 child 是否位于 path 内（Windows 大小写不敏感）。"""
    parent_parts = _windows_parts(path)
    child_parts = _windows_parts(child)
    return child_parts[: len(parent_parts)] == parent_parts


class Guard:
    """系统关键路径黑名单 + 运行中程序目录检测。"""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        self._executable = (
            Path(executable_path).resolve()
            if executable_path is not None
            else Path(sys.executable).resolve()
        )

    def check(self, path: str | Path, *, skip_running_check: bool = False) -> GuardResult:
        value = os.path.expanduser(os.fspath(path))
        # Windows 路径在 Linux/CI 上不能做 POSIX abspath，否则 C:\ 会被拼到当前目录。
        raw = value if _is_windows_style_path(value) else os.path.abspath(value)
        result = GuardResult()

        if _is_windows_style_path(raw):
            drive, tail = ntpath.splitdrive(raw)
            normalized_tail = tail.replace("/", "\\")
            if drive and normalized_tail in ("", "\\"):
                result.blocked.append(GuardIssue("drive_root", raw))
            parts = _windows_parts(raw)
            anchor = PureWindowsPath(raw).anchor
            if anchor and len(parts) == 1 and not drive:
                pass
            if len(parts) >= 2 and parts[1] in SYSTEM_COMPONENTS:
                result.blocked.append(GuardIssue("windows_dir", raw))
            if len(parts) >= 2 and parts[1].startswith(PROGRAM_FILES_PREFIX):
                result.blocked.append(GuardIssue("program_files", raw))
            if len(parts) >= 2 and parts[1] in SYSTEM_VOLUME_COMPONENTS:
                result.blocked.append(GuardIssue("system_volume_component", raw))
        else:
            # POSIX（开发/测试环境）也拒绝根目录，行为与 Windows 盘符根一致。
            normalized = os.path.normpath(raw)
            if normalized in ("/", "//"):
                result.blocked.append(GuardIssue("filesystem_root", raw))

        if not skip_running_check:
            self._check_running_program(raw, result)
        return result

    def _check_running_program(self, raw: str, result: GuardResult) -> None:
        """尽力检测：优先检查当前进程可执行文件；可选 psutil 扫描其他进程。"""
        exe = os.fspath(self._executable)
        running: list[str] = [exe]

        try:
            import psutil  # type: ignore[import-not-found]

            for proc in psutil.process_iter(["exe"]):
                try:
                    candidate = proc.info.get("exe")  # type: ignore[union-attr]
                except (psutil.NoSuchProcess, psutil.AccessDenied):  # type: ignore[attr-defined]
                    continue
                if candidate:
                    running.append(candidate)
        except ImportError:
            pass

        if _is_windows_style_path(raw):
            path_contains = _path_contains
        else:
            raw_parts = Path(raw).resolve().parts

            def path_contains(_path: str, child: str) -> bool:
                child_parts = Path(child).resolve().parts
                return child_parts[: len(raw_parts)] == raw_parts

        victims = sorted({p for p in running if path_contains(raw, p)})
        if victims:
            result.confirmations.append(GuardIssue("running_program", raw, "；".join(victims)))


def check_guard(
    path: str | Path,
    *,
    executable_path: str | Path | None = None,
    skip_running_check: bool = False,
) -> GuardResult:
    return Guard(executable_path=executable_path).check(path, skip_running_check=skip_running_check)


def humanize_blocked_reasons(issues: Iterable[GuardIssue]) -> str:
    """把拦截原因转成给用户看的中英双语消息。"""
    zh = {
        "drive_root": "不能操作盘符根目录",
        "windows_dir": "不能操作 Windows 目录",
        "program_files": "不能操作 Program Files 目录",
        "system_volume_component": "不能操作系统卷关键目录",
        "filesystem_root": "不能操作文件系统根目录",
    }
    en = {
        "drive_root": "Drive roots are protected",
        "windows_dir": "The Windows directory is protected",
        "program_files": "Program Files directories are protected",
        "system_volume_component": "System volume directories are protected",
        "filesystem_root": "File system roots are protected",
    }
    unique = {issue.reason: issue for issue in issues}
    return "；".join(zh.get(r, r) for r in unique) + " / " + "; ".join(en.get(r, r) for r in unique)
