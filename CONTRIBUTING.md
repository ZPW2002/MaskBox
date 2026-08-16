# Contributing to MaskBox

感谢你的贡献 / Thanks for contributing to MaskBox.

本项目只做本地文件夹管理，**绝不引入遥测**。任何路径信息只能进入用户本地数据库和本地日志，禁止进入 git、日志上传或任何网络请求。

## 本地开发

### 1. 后端（Linux / Windows 均可）

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check backend shell tests
black --check backend shell tests
```

核心分层原则：`backend/core` **不允许** import Flask 或 webview。API 与 pywebview 壳只是引擎的两个消费者。

### 2. 前端

需要 Node.js 18+：

```bash
cd frontend
npm install
npm run dev
npm run typecheck
npm run build
```

开发模式下 Vite 会把 `/api` 代理到 `http://127.0.0.1:5000`；实际桌面壳会自动选择随机端口。

### 3. 运行桌面壳（Windows）

```bash
python shell/main.py
```

依赖 Windows 10 1809+ 自带的 WebView2 运行时。

## 代码风格

- Python：`ruff`（line-length 100）+ `black`；公共函数必须有类型标注。
- 前端：TypeScript strict + ESLint 风格常识；文案必须中英成对出现在 `frontend/src/i18n/index.ts`。
- 提交信息：Conventional Commits（`feat:` `fix:` `docs:` `chore:`）。
- SQL：动态值一律参数化，禁止 f-string 拼 SQL（DDL 除外）。

## Pull Request 流程

1. 从 `main` 创建 feature 分支；
2. 写/改测试并确保 `pytest` 全绿；
3. 确保 `npm run typecheck` 通过；
4. 提交信息符合 Conventional Commits；
5. 发起 PR，填写模板。

## 隐私红线

- 任何路径信息只进本地 db/日志；
- 禁止引入遥测、统计 SDK；
- 旧 `data.db` 或包含真实路径的文件不能提交。
