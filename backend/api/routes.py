"""v2 REST API（1-11 / 1-12 / 1-13）。

所有接口统一 ``{code,msg,data}``；文件操作失败时尽力回滚到一致状态。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, request

from backend import __version__
from backend.api.errors import ApiError
from backend.core.guard import humanize_blocked_reasons
from backend.core.hide_service import HideError
from backend.core.mask_engine import (
    MaskConflictError,
    MaskSourceError,
    MaskValidationError,
    apply_mask,
    disguised_path,
    remove_mask,
)
from backend.storage.db import Database, IntegrityError, NotFoundError, folder_to_dict
from backend.storage.models import FolderRecord, MaskRecord

log = logging.getLogger("maskbox.api")

_MISSING = object()
_FOLDER_SORTS = {"name", "path", "created_at", "updated_at", "status"}

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _db() -> Database:
    return current_app.extensions["maskbox_db"]


def _hide() -> Any:
    return current_app.extensions["maskbox_hide_service"]


def _guard() -> Any:
    return current_app.extensions["maskbox_guard"]


def _locale() -> str:
    from backend.api.i18n import negotiate_locale

    return negotiate_locale(request.args, request.headers)


def _payload() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "error.bad_json")
    return data


def _normalize_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, "error.path_required")
    cleaned = os.path.expanduser(value.strip())
    # Windows 风格路径在 Linux/CI 上不能做 POSIX abspath；用 ntpath.normpath
    # 统一斜杠方向、消掉尾部分隔符，否则 "D:/foo" 与 "D:\foo\" 会成为两条记录。
    import ntpath

    if ntpath.splitdrive(cleaned)[0]:
        return ntpath.normpath(cleaned)
    return os.path.abspath(cleaned)


def _validated_mask_id(db: Database, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(400, "error.mask_invalid")
    mask = db.get_mask(value)
    if mask is None:
        raise ApiError(404, "error.mask_not_found")
    return int(value)


def _guard_check(raw_path: str) -> None:
    payload = request.get_json(silent=True) if request.method in ("POST", "PATCH") else None
    force = bool((payload or {}).get("force", False))
    result = _guard().check(raw_path)
    if result.blocked:
        reasons = humanize_blocked_reasons(result.blocked)
        raise ApiError(
            403,
            "error.guard_blocked",
            data={**result.to_dict(), "message": reasons},
        )
    if result.confirmations and not force:
        raise ApiError(
            409,
            "error.running_program",
            data={"reason": "running_program", "require_confirmation": True, **result.to_dict()},
        )


def _physical_state(record: FolderRecord, mask: MaskRecord | None) -> tuple[Path | None, bool]:
    """返回 (当前真实路径, 当前是否处于伪装状态)；两者都不存在则路径为 None。"""
    original = Path(record.original_path)
    masked = disguised_path(original, mask)
    if original.exists():
        return original, False
    if mask is not None and masked != original and masked.exists():
        return masked, True
    return None, False


def _serialize_folder(
    record: FolderRecord, masks: dict[int | None, MaskRecord | None]
) -> dict[str, Any]:
    mask = masks.get(record.mask_id)
    item = folder_to_dict(record, mask)
    current, is_masked = _physical_state(record, mask)
    if current is None:
        item["current_path"] = str(disguised_path(Path(record.original_path), mask))
        item["missing"] = True
    else:
        item["current_path"] = str(current)
        item["missing"] = False
    item["is_masked"] = is_masked or (
        mask is not None and current is not None and not Path(record.original_path).exists()
    )
    return item


def _raise_filesystem_error(exc: Exception) -> None:
    if isinstance(exc, MaskSourceError):
        raise ApiError(404, "error.path_not_dir") from exc
    if isinstance(exc, MaskConflictError):
        raise ApiError(409, "error.path_conflict", data={"detail": str(exc)}) from exc
    if isinstance(exc, HideError):
        raise ApiError(400, "error.operation_failed", data={"detail": str(exc)}) from exc
    if isinstance(exc, IntegrityError):
        raise ApiError(409, "error.duplicate_folder", data={"detail": str(exc)}) from exc
    raise exc


# ----------------------------------------------------------------------
# folder routes
# ----------------------------------------------------------------------
@api_bp.get("/folders")
def list_folders():
    db = _db()
    search = (request.args.get("search") or "").strip()
    sort = (request.args.get("sort") or "created_at").strip().lower()
    if sort not in _FOLDER_SORTS:
        sort = "created_at"
    records = db.list_folders(search=search, sort=sort)
    mask_map: dict[int | None, MaskRecord | None] = {m.id: m for m in db.list_masks()}
    mask_map[None] = None
    data = [_serialize_folder(record, mask_map) for record in records]
    from backend.api.i18n import translate

    return {"code": 200, "msg": translate("query_ok", _locale()), "data": data}


@api_bp.post("/folders")
def create_folder():
    payload = _payload()
    raw_path = _normalize_path(payload.get("path"))
    db = _db()
    hidden = _parse_bool(payload.get("hidden", False), "hidden")
    mask_id = _validated_mask_id(db, payload.get("mask_id"))
    display_name = _parse_display_name(payload.get("display_name"), raw_path)
    _guard_check(raw_path)

    if db.get_folder_by_original_path(raw_path) is not None:
        raise ApiError(409, "error.duplicate_folder")

    folder = Path(raw_path)
    if not folder.is_dir():
        raise ApiError(400, "error.path_not_dir")

    mask = db.get_mask(mask_id) if mask_id is not None else None
    hide_service = _hide()
    mask_applied = False
    try:
        hide_service.set_hidden(folder, hidden)
        if mask is not None:
            apply_mask(folder, mask)
            mask_applied = True
        record = db.create_folder(raw_path, display_name, hidden, mask_id)
    except Exception as exc:  # noqa: BLE001 - rollback on every failure
        log.exception("create_folder failed; rolling back filesystem changes")
        if mask_applied:
            try:
                remove_mask(folder, mask)
            except Exception:
                log.exception("rollback remove_mask failed")
        try:
            hide_service.set_hidden(folder, False)
        except Exception:
            log.exception("rollback unhide failed")
        _raise_filesystem_error(exc)
        raise ApiError(500, "error.operation_failed", data={"detail": str(exc)}) from exc

    from backend.api.i18n import translate

    return {
        "code": 200,
        "msg": translate("created_ok", _locale()),
        "data": _serialize_folder(record, {record.mask_id: mask, None: None}),
    }


@api_bp.patch("/folders/<int:folder_id>")
def update_folder(folder_id: int):
    return _perform_update_folder(folder_id, _payload())


def _perform_update_folder(folder_id: int, payload: dict[str, Any]):
    db = _db()
    record = db.get_folder(folder_id)
    if record is None:
        raise ApiError(404, "error.folder_not_found")

    old_mask = db.get_mask(record.mask_id) if record.mask_id is not None else None
    new_hidden = (
        record.hidden if "hidden" not in payload else _parse_bool(payload.get("hidden"), "hidden")
    )
    new_mask_id = (
        record.mask_id
        if "mask_id" not in payload
        else _validated_mask_id(db, payload.get("mask_id"))
    )
    new_display_name = (
        record.display_name
        if "display_name" not in payload
        else _parse_display_name(payload.get("display_name"), record.original_path)
    )
    new_mask = db.get_mask(new_mask_id) if new_mask_id is not None else None
    original = Path(record.original_path)

    physical, was_masked = _physical_state(record, old_mask)
    filesystem_changed = new_hidden != record.hidden or new_mask_id != record.mask_id
    if physical is None and filesystem_changed:
        raise ApiError(404, "error.missing_target", data={"id": record.id})
    if physical is None:
        updated = db.update_folder(folder_id, display_name=new_display_name)
        from backend.api.i18n import translate

        return {
            "code": 200,
            "msg": translate("updated_ok", _locale()),
            "data": _serialize_folder(updated, {updated.mask_id: new_mask, None: None}),
        }

    hide_service = _hide()
    old_mask_removed = False
    new_mask_applied = False
    try:
        if physical is not None and was_masked and new_mask_id != record.mask_id:
            remove_mask(original, old_mask)
            physical = original
            old_mask_removed = True
        hide_service.set_hidden(physical, new_hidden)
        if new_mask is not None:
            apply_mask(original, new_mask)
            new_mask_applied = True
        updated = db.update_folder(
            folder_id,
            display_name=new_display_name,
            hidden=new_hidden,
            mask_id=new_mask_id,
        )
    except Exception as exc:  # noqa: BLE001 - rollback to previous physical state
        log.exception("update_folder failed; rolling back filesystem changes")
        _rollback_update(
            original, old_mask, new_mask, old_mask_removed, new_mask_applied, record.hidden
        )
        _raise_filesystem_error(exc)
        raise ApiError(500, "error.operation_failed", data={"detail": str(exc)}) from exc

    from backend.api.i18n import translate

    return {
        "code": 200,
        "msg": translate("updated_ok", _locale()),
        "data": _serialize_folder(updated, {updated.mask_id: new_mask, None: None}),
    }


def _rollback_update(
    original: Path,
    old_mask: MaskRecord | None,
    new_mask: MaskRecord | None,
    old_mask_removed: bool,
    new_mask_applied: bool,
    old_hidden: bool,
) -> None:
    hide_service = _hide()
    if new_mask_applied and new_mask is not None:
        try:
            remove_mask(original, new_mask)
        except Exception:
            log.exception("rollback remove new mask failed")
    if old_mask_removed and old_mask is not None:
        try:
            apply_mask(original, old_mask)
        except Exception:
            log.exception("rollback re-apply old mask failed")
    target = disguised_path(original, old_mask) if old_mask_removed else original
    try:
        hide_service.set_hidden(target, old_hidden)
    except Exception:
        log.exception("rollback restore hidden attribute failed")


@api_bp.delete("/folders/<int:folder_id>")
def delete_folder(folder_id: int):
    db = _db()
    record = db.get_folder(folder_id)
    if record is None:
        raise ApiError(404, "error.folder_not_found")

    old_mask = db.get_mask(record.mask_id) if record.mask_id is not None else None
    original = Path(record.original_path)
    physical, was_masked = _physical_state(record, old_mask)
    hide_service = _hide()
    mask_removed = False
    try:
        if physical is not None and was_masked and old_mask is not None:
            remove_mask(original, old_mask)
            physical = original
            mask_removed = True
        if physical is not None:
            hide_service.set_hidden(physical, False)
        db.delete_folder(folder_id)
    except Exception as exc:  # noqa: BLE001 - restore if DB deletion fails
        log.exception("delete_folder failed; restoring filesystem state")
        if mask_removed and old_mask is not None:
            try:
                apply_mask(original, old_mask)
            except Exception:
                log.exception("delete rollback mask failed")
        try:
            target = disguised_path(original, old_mask) if mask_removed else original
            if target.exists():
                hide_service.set_hidden(target, record.hidden)
        except Exception:
            log.exception("delete rollback hidden failed")
        _raise_filesystem_error(exc)
        raise ApiError(500, "error.operation_failed", data={"detail": str(exc)}) from exc

    from backend.api.i18n import translate

    return {"code": 200, "msg": translate("deleted_ok", _locale()), "data": {"id": folder_id}}


@api_bp.post("/folders/<int:folder_id>/toggle-hide")
def toggle_hide(folder_id: int):
    db = _db()
    record = db.get_folder(folder_id)
    if record is None:
        raise ApiError(404, "error.folder_not_found")
    payload = _payload() if request.is_json else {}
    payload.setdefault("hidden", not record.hidden)
    payload.setdefault("mask_id", record.mask_id)
    return _perform_update_folder(folder_id, payload)


# ----------------------------------------------------------------------
# mask routes
# ----------------------------------------------------------------------
@api_bp.get("/masks")
def list_masks():
    db = _db()
    from backend.api.i18n import translate

    return {
        "code": 200,
        "msg": translate("query_ok", _locale()),
        "data": [m.to_dict() for m in db.list_masks()],
    }


@api_bp.post("/masks")
def create_mask():
    db = _db()
    payload = _payload()
    name = payload.get("name")
    clsid = payload.get("clsid")
    if not isinstance(name, str) and name is not None:
        raise ApiError(400, "error.mask_invalid")
    try:
        mask = db.create_custom_mask(name or "", clsid)
    except MaskValidationError as exc:
        raise ApiError(400, "error.mask_invalid", data={"detail": str(exc)}) from exc
    except IntegrityError as exc:
        raise ApiError(409, "error.duplicate_mask", data={"detail": str(exc)}) from exc

    from backend.api.i18n import translate

    return {"code": 200, "msg": translate("mask_created_ok", _locale()), "data": mask.to_dict()}


@api_bp.patch("/masks/<int:mask_id>")
def update_mask(mask_id: int):
    db = _db()
    payload = _payload()
    existing = db.get_mask(mask_id)
    if existing is None:
        raise ApiError(404, "error.mask_not_found")
    if existing.builtin:
        raise ApiError(409, "error.builtin_mask")

    if db.count_folders_using_mask(mask_id) > 0:
        if "name" in payload and payload.get("name") != existing.name:
            raise ApiError(409, "error.mask_in_use", data={"reason": "mask_in_use"})
        if "clsid" in payload and payload.get("clsid") != existing.clsid:
            raise ApiError(409, "error.mask_in_use", data={"reason": "mask_in_use"})

    name = payload.get("name") if "name" in payload else None
    clsid = payload.get("clsid") if "clsid" in payload else None
    try:
        mask = db.update_custom_mask(mask_id, name=name, clsid=clsid)
    except MaskValidationError as exc:
        raise ApiError(400, "error.mask_invalid", data={"detail": str(exc)}) from exc
    except IntegrityError as exc:
        raise ApiError(409, "error.duplicate_mask", data={"detail": str(exc)}) from exc
    except NotFoundError as exc:
        raise ApiError(404, "error.mask_not_found") from exc

    from backend.api.i18n import translate

    return {"code": 200, "msg": translate("mask_updated_ok", _locale()), "data": mask.to_dict()}


@api_bp.delete("/masks/<int:mask_id>")
def delete_mask(mask_id: int):
    db = _db()
    existing = db.get_mask(mask_id)
    if existing is None:
        raise ApiError(404, "error.mask_not_found")
    if existing.builtin:
        raise ApiError(409, "error.builtin_mask")
    if db.count_folders_using_mask(mask_id) > 0:
        raise ApiError(409, "error.mask_in_use", data={"reason": "mask_in_use"})
    try:
        db.delete_custom_mask(mask_id)
    except IntegrityError as exc:
        raise ApiError(409, "error.mask_in_use", data={"detail": str(exc)}) from exc

    from backend.api.i18n import translate

    return {"code": 200, "msg": translate("mask_deleted_ok", _locale()), "data": {"id": mask_id}}


@api_bp.get("/health")
def health():
    cfg = current_app.config["MASKBOX_STORAGE"]
    return {
        "code": 200,
        "msg": "ok",
        "data": {
            "status": "ok",
            "version": __version__,
            "portable": cfg.portable,
            "platform": os.name,
        },
    }


# ----------------------------------------------------------------------
# payload helpers
# ----------------------------------------------------------------------
def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("是", "true", "1", "yes", "y"):
            return True
        if lowered in ("否", "false", "0", "no", "n"):
            return False
    raise ApiError(400, "error.folder_invalid", data={"field": field})


def _parse_display_name(value: Any, fallback_path: str) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return Path(fallback_path).name or fallback_path
    if not isinstance(value, str) or len(value.strip()) > 255:
        raise ApiError(400, "error.folder_invalid", data={"field": "display_name"})
    return value.strip()
