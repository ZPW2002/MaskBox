# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：MaskBox Windows 便携版（单目录）。"""
from PyInstaller.utils.hooks import collect_all

webview_datas, webview_binaries, webview_hiddenimports = collect_all("webview")

datas = [("../frontend/dist", "frontend/dist")] + webview_datas
binaries = webview_binaries
hiddenimports = webview_hiddenimports + [
    "flask",
    "werkzeug",
    "backend.api",
    "backend.core.guard",
    "backend.core.hide_service",
    "backend.core.mask_engine",
    "backend.storage.config",
    "backend.storage.db",
    "backend.storage.models",
]

a = Analysis(
    ["shell/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc", "test"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MaskBox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MaskBox",
)
