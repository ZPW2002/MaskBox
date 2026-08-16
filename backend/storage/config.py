"""数据目录与日志目录策略（D13 / 1-8 / 1-16）。

规则：
- 优先使用 ``%APPDATA%\\MaskBox\\data.db``；
- 程序目录存在 ``portable.txt`` 时，数据和日志都跟随程序目录；
- 日志位于 ``%LOCALAPPDATA%\\MaskBox\\logs\\``（便携模式在程序目录 ``logs\\``）。
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "MaskBox"
PORTABLE_MARKER = "portable.txt"


def _resource_root() -> Path:
    """代码/静态资源所在目录。

    PyInstaller onedir 打包后资源被解到 ``sys._MEIPASS``，而可执行文件在
    ``sys.executable`` 同级的目录。便携模式检测只应看可执行文件目录。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def _program_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """MaskBox 运行时路径配置。"""

    program_dir: Path
    resource_root: Path
    portable: bool
    db_path: Path
    log_dir: Path
    legacy_db_paths: tuple[Path, ...]

    @property
    def frontend_dist(self) -> Path:
        return self.resource_root / "frontend" / "dist"

    @property
    def legacy_db_candidates(self) -> tuple[Path, ...]:
        return self.legacy_db_paths

    @classmethod
    def resolve(
        cls,
        *,
        program_dir: str | Path | None = None,
        resource_root: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> StorageConfig:
        """按 D13 解析数据目录。

        测试可直接传入 ``env`` 覆盖 ``APPDATA`` / ``LOCALAPPDATA``，避免污染真实用户目录。
        """
        environ = os.environ if env is None else env
        program = Path(program_dir) if program_dir else _program_dir()
        resources = Path(resource_root) if resource_root else _resource_root()
        portable = (program / PORTABLE_MARKER).is_file()

        if portable:
            data_dir = program / "data"
            log_dir = program / "logs"
        else:
            if os.name == "nt" and "APPDATA" in environ:
                data_base = Path(environ["APPDATA"]) / APP_NAME
            elif "MASKBOX_DATA_DIR" in environ:
                data_base = Path(environ["MASKBOX_DATA_DIR"])
            else:
                # Linux/CI 兜底，真实 Windows 产品不会走到这里。
                data_base = Path.home() / ".local" / "share" / APP_NAME

            data_dir = data_base
            if "MASKBOX_LOG_DIR" in environ:
                log_dir = Path(environ["MASKBOX_LOG_DIR"])
            elif os.name == "nt" and "LOCALAPPDATA" in environ:
                log_dir = Path(environ["LOCALAPPDATA"]) / APP_NAME / "logs"
            else:
                log_dir = data_base / "logs"

        legacy = (
            program / "python-flask" / "data" / "data.db",
            program / "data" / "data.db",
            Path.cwd() / "python-flask" / "data" / "data.db",
            Path.cwd() / "data" / "data.db",
        )
        # 去重并排除目标库自身（避免便携模式下 data/data.db 被当成旧库）。
        unique: list[Path] = []
        for candidate in legacy:
            resolved = Path(os.path.abspath(candidate))
            if resolved not in unique:
                unique.append(resolved)
        legacy_paths = tuple(p for p in unique if p != Path(os.path.abspath(data_dir / "data.db")))

        return cls(
            program_dir=program,
            resource_root=resources,
            portable=portable,
            db_path=data_dir / "data.db",
            log_dir=log_dir,
            legacy_db_paths=legacy_paths,
        )

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def is_portable(program_dir: str | Path | None = None) -> bool:
    program = Path(program_dir) if program_dir else _program_dir()
    return (program / PORTABLE_MARKER).is_file()
