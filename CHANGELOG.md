# Changelog

本项目的所有值得注意的变更都会记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [2.0.1] - 2026-08-16

### Fixed

- 修复 PyInstaller 冻结后前端资源目录解析错误：发布包运行时不再显示 “Frontend not built”。
- 添加冻结路径回归测试（`sys._MEIPASS/frontend/dist`）。

## [2.0.0] - 2026-08-10

MaskBox 首个公开版本（由 HideTool 全面重构并更名）。

### Added

- 后端引擎分层：`backend/core` 不依赖 Flask/webview，可独立测试
- 可自定义面具引擎：内置 8 种 CLSID 面具，支持名称伪装与自定义 CLSID
- v2 API：搜索、排序、批量、toggle-hide、面具管理、健康检查
- SQLite 全参数化、TEXT 路径字段、旧 `data.db` 自动迁移
- 安全加固：仅绑定 127.0.0.1、系统关键路径防呆、失败回滚
- `%APPDATA%\MaskBox\` 数据目录与便携模式（`portable.txt`）
- 日志落地 `%LOCALAPPDATA%\MaskBox\logs\`（便携模式随程序目录）
- Vue3 + TypeScript + Vite + Element Plus 浅色 UI
- 中英双语（vue-i18n，后端 msg 同步双语）
- 拖拽添加（pywebview DOM 桥接 WebView2 真实路径）
- 丢失项提示与清理
- pytest、ruff/black、GitHub Actions CI、Windows 便携版打包

### Changed

- 项目名 HideTool → MaskBox（中文名：面具盒）
- 不再把拼接后的伪装路径写入数据库
- 目录选择改用 pywebview 原生对话框，移除 tkinter 代码
- 发布形态改为 `MaskBox-vX.Y.Z-windows-portable.zip`

### Removed

- 旧 Vue2 构建产物、`python-flask/build/`、`python-flask/dist/`、`__pycache__/`、`data/data.db` 均从 git 历史移除
- 无遥测、无密码/加密功能（按 D3 决策）
