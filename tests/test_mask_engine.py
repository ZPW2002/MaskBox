from __future__ import annotations

from pathlib import Path

import pytest

from backend.core.mask_engine import (
    BUILTIN_MASKS,
    BuiltinMaskSpec,
    MaskConflictError,
    MaskRegistry,
    MaskSourceError,
    MaskValidationError,
    apply_mask,
    disguised_path,
    remove_mask,
)


def test_builtin_masks_have_eight_clsid_masks() -> None:
    assert len(BUILTIN_MASKS) == 8
    assert all(spec.clsid for spec in BUILTIN_MASKS)


@pytest.mark.parametrize(
    ("clsid", "expected"),
    [
        ("645ff040-5081-101b-9f08-00aa002f954e", "{645FF040-5081-101B-9F08-00AA002F954E}"),
        ("{645ff040-5081-101b-9f08-00aa002f954e}", "{645FF040-5081-101B-9F08-00AA002F954E}"),
        ("", None),
        (None, None),
    ],
)
def test_validate_clsid(clsid: str | None, expected: str | None) -> None:
    assert MaskRegistry.validate_clsid(clsid) == expected


@pytest.mark.parametrize("bad", ["not-a-guid", "{zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz}"])
def test_validate_clsid_rejects_bad_values(bad: str) -> None:
    with pytest.raises(MaskValidationError):
        MaskRegistry.validate_clsid(bad)


@pytest.mark.parametrize("bad_name", ["", "  ", "a/b", "CON"])
def test_validate_name_rejects_bad_names(bad_name: str) -> None:
    with pytest.raises(MaskValidationError):
        MaskRegistry.validate_name(bad_name)


def test_apply_and_remove_clsid_mask(tmp_path: Path) -> None:
    folder = tmp_path / "secret"
    folder.mkdir()
    mask = BUILTIN_MASKS[1]  # 回收站

    target = apply_mask(folder, mask)
    assert target.name == "secret.{645FF040-5081-101B-9F08-00AA002F954E}"
    assert target.is_dir()
    assert not folder.exists()

    restored = remove_mask(folder, mask)
    assert restored == folder
    assert folder.is_dir()
    assert not target.exists()


def test_apply_same_mask_twice_does_not_stack(tmp_path: Path) -> None:
    folder = tmp_path / "mine"
    folder.mkdir()
    mask = BUILTIN_MASKS[0]

    first = apply_mask(folder, mask)
    second = apply_mask(folder, mask)  # 原路径不存在，但同面具目标存在 => 幂等
    assert first == second
    assert second.name.count(".{") == 1
    assert remove_mask(folder, mask) == folder


def test_apply_rejects_existing_target(tmp_path: Path) -> None:
    folder = tmp_path / "a"
    folder.mkdir()
    (tmp_path / "a.{645FF040-5081-101B-9F08-00AA002F954E}").mkdir()
    with pytest.raises(MaskConflictError):
        apply_mask(folder, BUILTIN_MASKS[1])


def test_name_only_mask_renames_to_custom_name(tmp_path: Path) -> None:
    folder = tmp_path / "private"
    folder.mkdir()
    mask = BuiltinMaskSpec("新建文件夹", None)

    target = apply_mask(folder, mask)
    assert target == tmp_path / "新建文件夹"
    assert target.is_dir()

    restored = remove_mask(folder, mask)
    assert restored == folder


def test_remove_mask_is_idempotent(tmp_path: Path) -> None:
    folder = tmp_path / "idem"
    folder.mkdir()
    mask = BUILTIN_MASKS[2]
    apply_mask(folder, mask)
    remove_mask(folder, mask)
    assert remove_mask(folder, mask) == folder


def test_apply_missing_source_raises(tmp_path: Path) -> None:
    with pytest.raises(MaskSourceError):
        apply_mask(tmp_path / "ghost", BUILTIN_MASKS[0])


def test_restore_original_path_uses_known_suffix_not_first_dot(tmp_path: Path) -> None:
    """原文件夹名本身含 .{xxx} 时，旧 split('.{')[0] 会截断；这里应只剥已知后缀。"""
    stored = "F:/my.{11111111-1111-1111-1111-111111111111}.{645FF040-5081-101B-9F08-00AA002F954E}"
    original = MaskRegistry.restore_original_path(
        stored, "回收站", "{645FF040-5081-101B-9F08-00AA002F954E}"
    )
    assert original == "F:/my.{11111111-1111-1111-1111-111111111111}"


def test_disguised_path_is_pure(tmp_path: Path) -> None:
    mask = BuiltinMaskSpec("新建文件夹", None)
    assert disguised_path(tmp_path / "x", mask) == tmp_path / "新建文件夹"
    assert disguised_path(tmp_path / "x", None) == tmp_path / "x"
