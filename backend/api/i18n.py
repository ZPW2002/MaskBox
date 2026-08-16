"""API 文案中英双语（Phase 2-7 后端部分）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

DEFAULT_LOCALE = "zh"

MESSAGES: dict[str, dict[str, str]] = {
    "ok": {"zh": "操作成功", "en": "Success"},
    "query_ok": {"zh": "查询成功", "en": "Query succeeded"},
    "created_ok": {"zh": "添加成功", "en": "Folder added"},
    "updated_ok": {"zh": "修改成功", "en": "Folder updated"},
    "deleted_ok": {"zh": "删除成功", "en": "Folder deleted"},
    "toggle_ok": {"zh": "状态已切换", "en": "Status toggled"},
    "mask_created_ok": {"zh": "面具已创建", "en": "Mask created"},
    "mask_updated_ok": {"zh": "面具已更新", "en": "Mask updated"},
    "mask_deleted_ok": {"zh": "面具已删除", "en": "Mask deleted"},
    "dialog_ok": {"zh": "选择成功", "en": "Folder selected"},
    "error.bad_json": {"zh": "请求体不是合法的 JSON", "en": "Request body is not valid JSON"},
    "error.bad_request": {"zh": "请求参数错误", "en": "Bad request"},
    "error.path_required": {"zh": "请选择文件夹", "en": "Please select a folder"},
    "error.path_not_dir": {
        "zh": "路径不存在或不是文件夹",
        "en": "Path does not exist or is not a folder",
    },
    "error.not_found": {"zh": "接口不存在", "en": "Endpoint not found"},
    "error.folder_not_found": {
        "zh": "记录不存在或目标已丢失",
        "en": "Record not found or target is missing",
    },
    "error.mask_not_found": {"zh": "面具不存在", "en": "Mask not found"},
    "error.duplicate_folder": {"zh": "目录已存在", "en": "Folder already exists"},
    "error.duplicate_mask": {"zh": "面具名称已存在", "en": "Mask name already exists"},
    "error.mask_in_use": {
        "zh": "面具使用中，不能删除",
        "en": "Mask is in use and cannot be deleted",
    },
    "error.builtin_mask": {
        "zh": "内置面具不可修改或删除",
        "en": "Built-in masks cannot be modified or deleted",
    },
    "error.guard_blocked": {
        "zh": "操作被安全策略拒绝",
        "en": "Operation rejected by safety policy",
    },
    "error.running_program": {
        "zh": "目标目录可能包含正在运行的程序，确认要继续吗？",
        "en": "The target folder may contain a running program. Continue?",
    },
    "error.path_conflict": {"zh": "目标路径已存在，无法重命名", "en": "Target path already exists"},
    "error.missing_target": {
        "zh": "目标已丢失，可移除记录",
        "en": "Target is missing. You can remove the record",
    },
    "error.internal": {"zh": "服务器内部错误", "en": "Internal server error"},
    "error.method_not_allowed": {"zh": "请求方法不允许", "en": "Method not allowed"},
    "error.folder_invalid": {"zh": "文件夹参数不合法", "en": "Invalid folder parameters"},
    "error.mask_invalid": {"zh": "面具参数不合法", "en": "Invalid mask parameters"},
    "error.operation_failed": {
        "zh": "操作失败，文件状态已回滚",
        "en": "Operation failed; file state was rolled back",
    },
}


def negotiate_locale(query: Mapping[str, Any] | None, headers: Mapping[str, str]) -> str:
    """语言优先级：?lang= / X-Lang / Accept-Language；默认中文。"""
    if query:
        lang = query.get("lang")
        if isinstance(lang, str) and lang:
            return "en" if lang.lower().startswith("en") else "zh"
    if headers:
        lang = headers.get("X-Lang")
        if isinstance(lang, str) and lang:
            return "en" if lang.lower().startswith("en") else "zh"
        accept = headers.get("Accept-Language", "")
        if accept and accept.split(",", 1)[0].lower().startswith("en"):
            return "en"
    return DEFAULT_LOCALE


def translate(key: str, locale: str = DEFAULT_LOCALE, **values: Any) -> str:
    text = MESSAGES.get(key, {}).get(locale) or MESSAGES.get(key, {}).get(DEFAULT_LOCALE) or key
    if values:
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text
    return text
