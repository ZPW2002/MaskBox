from __future__ import annotations

from pathlib import Path

from backend.core.guard import Guard, GuardResult


def test_guard_rejects_drive_root() -> None:
    result = Guard(executable_path="/usr/bin/python3").check("C:\\")
    assert any(issue.reason == "drive_root" for issue in result.blocked)


def test_guard_rejects_windows_and_program_files() -> None:
    guard = Guard(executable_path="/usr/bin/python3")
    assert any(i.reason == "windows_dir" for i in guard.check("C:\\Windows\\System32").blocked)
    assert any(
        i.reason == "program_files" for i in guard.check("D:\\Program Files (x86)\\App").blocked
    )


def test_guard_rejects_system_volume_component() -> None:
    result = Guard(executable_path="/usr/bin/python3").check("C:\\System Volume Information")
    assert any(i.reason == "system_volume_component" for i in result.blocked)


def test_guard_allows_normal_folder(tmp_path: Path) -> None:
    folder = tmp_path / "normal"
    folder.mkdir()
    result: GuardResult = Guard(executable_path="/usr/bin/python3").check(folder)
    assert result.ok
    assert result.confirmations == []


def test_guard_detects_running_program_install_dir(tmp_path: Path) -> None:
    target = tmp_path / "app"
    target.mkdir()
    exe = target / "bin" / "app.exe"
    exe.parent.mkdir()
    exe.touch()
    result = Guard(executable_path=exe).check(target)
    # 只是运行中的程序目录：不拦截（blocked 为空），仅要求二次确认。
    assert result.ok
    assert result.blocked == []
    assert any(i.reason == "running_program" for i in result.confirmations)
