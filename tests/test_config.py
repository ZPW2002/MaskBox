from __future__ import annotations

from pathlib import Path

from backend.storage.config import StorageConfig


def test_portable_mode_follows_program_dir(tmp_path: Path) -> None:
    program = tmp_path / "program"
    program.mkdir()
    (program / "portable.txt").touch()
    cfg = StorageConfig.resolve(program_dir=program, resource_root=tmp_path / "res")
    assert cfg.portable is True
    assert cfg.db_path == program / "data" / "data.db"
    assert cfg.log_dir == program / "logs"


def test_roaming_mode_uses_overrides(tmp_path: Path) -> None:
    program = tmp_path / "program"
    program.mkdir()
    data = tmp_path / "roaming" / "MaskBox"
    logs = tmp_path / "local" / "MaskBox" / "logs"
    cfg = StorageConfig.resolve(
        program_dir=program,
        resource_root=tmp_path / "res",
        env={"MASKBOX_DATA_DIR": str(data), "MASKBOX_LOG_DIR": str(logs)},
    )
    assert cfg.portable is False
    assert cfg.db_path == data / "data.db"
    assert cfg.log_dir == logs
