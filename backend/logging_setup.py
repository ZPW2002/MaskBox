"""日志落地（1-16）：Windows 默认 ``%LOCALAPPDATA%\\MaskBox\\logs\\``。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(threadName)s: %(message)s"


def setup_logging(log_dir: str | Path, *, level: int = logging.INFO) -> None:
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        return
    root.setLevel(level)

    file_handler = RotatingFileHandler(
        directory / "maskbox.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(console)
