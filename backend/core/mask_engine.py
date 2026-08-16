"""面具引擎（D6 / 1-4 / 1-5 / 1-6）。

设计要点：
- DB 只保存 ``original_path + mask_id``，伪装后的真实路径永远实时计算；
- CLSID 面具通过 ``原名.{CLSID}`` 触发 Explorer 的命名空间伪装；
- CLSID 留空时退化为「名称伪装」，直接把目录改名为面具名（例如「新建文件夹」）；
- 所有 rename 都具备幂等性，重复 apply 不会叠加后缀。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

GUID_PATTERN = re.compile(
    r"^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-" r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$"
)
WINDOWS_INVALID_NAME_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


@dataclass(frozen=True, slots=True)
class BuiltinMaskSpec:
    name: str
    clsid: str | None


class MaskLike(Protocol):
    name: str
    clsid: str | None


BUILTIN_MASKS: tuple[BuiltinMaskSpec, ...] = (
    BuiltinMaskSpec("无关联文件", "{00021401-0000-0000-C000-000000000046}"),
    BuiltinMaskSpec("回收站", "{645FF040-5081-101B-9F08-00AA002F954E}"),
    BuiltinMaskSpec("脱机文件夹", "{AFDB1F70-2A4C-11D2-9039-00C04F8EEB3E}"),
    BuiltinMaskSpec("管理工具", "{D20EA4E1-3957-11D2-A40B-0C5020524153}"),
    BuiltinMaskSpec("历史记录", "{FF393560-C2A7-11CF-BFF4-444553540000}"),
    BuiltinMaskSpec("缓存文件夹", "{88C6C381-2E85-11D0-94DE-444553540000}"),
    BuiltinMaskSpec("拨号网络", "{992CFFA0-F557-101A-88EC-00DD010CCC48}"),
    BuiltinMaskSpec("网上邻居", "{208D2C60-3AEA-1069-A2D7-08002B30309D}"),
)

BUILTIN_BY_NAME = {mask.name.casefold(): mask for mask in BUILTIN_MASKS}


class MaskValidationError(ValueError):
    """面具定义不合法。"""


class MaskConflictError(FileExistsError):
    """目标路径已存在，rename 无法安全执行。"""


class MaskSourceError(FileNotFoundError):
    """源路径不存在或不是目录。"""


class MaskRegistry:
    """内置面具注册表 + 自定义面具校验。"""

    @staticmethod
    def builtin_masks() -> tuple[BuiltinMaskSpec, ...]:
        return BUILTIN_MASKS

    @staticmethod
    def validate_name(name: str) -> str:
        """校验面具名称，返回去除首尾空白后的名称。"""
        if not isinstance(name, str):
            raise MaskValidationError("面具名称必须是字符串 / Mask name must be a string")
        clean = name.strip()
        if not clean:
            raise MaskValidationError("面具名称不能为空 / Mask name cannot be empty")
        if len(clean) > 100:
            raise MaskValidationError("面具名称不能超过 100 个字符 / Mask name is too long")
        if any(ch in WINDOWS_INVALID_NAME_CHARS for ch in clean):
            raise MaskValidationError(
                "面具名称包含非法字符 / Mask name contains invalid characters"
            )
        if clean in (".", ".."):
            raise MaskValidationError("面具名称不合法 / Invalid mask name")
        if clean.endswith((" ", ".")):
            raise MaskValidationError(
                "面具名称不能以空格或点结尾 / Mask name cannot end with space or dot"
            )
        base = clean.split(".", 1)[0].upper()
        if base in WINDOWS_RESERVED_NAMES:
            raise MaskValidationError(
                "面具名称是 Windows 保留名 / Mask name is reserved by Windows"
            )
        return clean

    @staticmethod
    def validate_clsid(clsid: str | None, *, allow_empty: bool = True) -> str | None:
        """校验并标准化 GUID，返回带花括号的大写形式；空值返回 None。"""
        if clsid is None:
            return None
        if not isinstance(clsid, str):
            raise MaskValidationError("CLSID 必须是字符串 / CLSID must be a string")
        value = clsid.strip()
        if value == "":
            if allow_empty:
                return None
            raise MaskValidationError("CLSID 不能为空 / CLSID cannot be empty")
        if not GUID_PATTERN.fullmatch(value):
            raise MaskValidationError("CLSID 不是合法的 GUID / CLSID is not a valid GUID")
        value = value.strip("{}")
        return "{" + value.upper() + "}"

    @staticmethod
    def suffix_for(clsid: str | None) -> str:
        """返回 Explorer 伪装后缀；无 CLSID 时返回空串。"""
        normalized = MaskRegistry.validate_clsid(clsid, allow_empty=True)
        return f".{normalized}" if normalized else ""

    @staticmethod
    def restore_original_path(stored_path: str, mask_name: str, clsid: str | None) -> str:
        """旧版数据路径还原（1-9）。

        旧版把 ``original + mask_dic(mask)`` 拼在一起，并错误地用
        ``split('.{')[0]`` 还原。这里优先按**已知 CLSID 后缀**精确剥离；
        找不到后缀时才回退到旧的 split 行为，最大限度兼容原数据。
        """
        suffix = MaskRegistry.suffix_for(clsid)
        if suffix and stored_path.casefold().endswith(suffix.casefold()):
            return stored_path[: -len(suffix)]
        if suffix and ".{" in stored_path:
            return stored_path.split(".{", 1)[0]
        return stored_path


def _same_path(left: Path, right: Path) -> bool:
    left_abs = os.path.abspath(os.path.normcase(os.fspath(left)))
    right_abs = os.path.abspath(os.path.normcase(os.fspath(right)))
    return left_abs == right_abs


def disguised_path(original_path: str | Path, mask: MaskLike | None) -> Path:
    """计算应用面具后的真实路径（纯函数，不碰文件系统）。"""
    original = Path(original_path)
    if mask is None:
        return original

    clsid = MaskRegistry.validate_clsid(getattr(mask, "clsid", None), allow_empty=True)
    if clsid:
        return original.parent / f"{original.name}{MaskRegistry.suffix_for(clsid)}"
    return original.parent / MaskRegistry.validate_name(getattr(mask, "name", ""))


def apply_mask(
    original_path: str | Path,
    mask: MaskLike,
    *,
    rename=os.rename,
) -> Path:
    """把 ``original_path`` 伪装成 ``mask`` 描述的样子，返回伪装后的路径。

    幂等规则：源已经是目标路径，或源名已经带同一 CLSID 后缀时直接返回。
    """
    original = Path(original_path)
    target = disguised_path(original, mask)
    if _same_path(original, target):
        if original.exists() or original.is_symlink():
            return target
        raise MaskSourceError(f"目录不存在: {original} / Directory does not exist: {original}")

    clsid = MaskRegistry.validate_clsid(getattr(mask, "clsid", None), allow_empty=True)
    if (
        clsid
        and original.exists()
        and original.name.casefold().endswith(MaskRegistry.suffix_for(clsid).casefold())
    ):
        return original

    original_exists = original.exists() or original.is_symlink()
    target_exists = target.exists() or target.is_symlink()

    # 幂等：原路径已不在、但同面具目标路径存在，说明已经 apply 过。
    if not original_exists and target_exists:
        return target

    if not original_exists:
        raise MaskSourceError(f"目录不存在: {original} / Directory does not exist: {original}")
    if target_exists:
        raise MaskConflictError(f"目标已存在: {target} / Target already exists: {target}")

    rename(original, target)
    return target


def remove_mask(
    original_path: str | Path,
    mask: MaskLike | None,
    *,
    rename=os.rename,
) -> Path:
    """撤销伪装，把当前伪装目录改回 ``original_path``。

    同时兼容「物理目录已经叫 original_path」的情况（重复恢复幂等）。
    """
    original = Path(original_path)
    target = disguised_path(original, mask)
    original_exists = original.exists() or original.is_symlink()
    target_exists = target.exists() or target.is_symlink()

    if _same_path(original, target):
        if original_exists:
            return original
        raise MaskSourceError(f"目录不存在: {original} / Directory does not exist: {original}")

    if original_exists and not target_exists:
        return original
    if target_exists and not original_exists:
        rename(target, original)
        return original
    if target_exists and original_exists:
        raise MaskConflictError(
            f"伪装路径和原路径同时存在: {target} / Both masked and original paths exist"
        )
    raise MaskSourceError(f"目录不存在: {original} / Directory does not exist: {original}")


# 旧代码使用了这个名称，保留兼容别名。
mask_target = disguised_path
split_disguised_path = MaskRegistry.restore_original_path
