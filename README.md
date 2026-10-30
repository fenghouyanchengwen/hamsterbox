# 仓鼠盒（LMMDB / HamsterBox）

本地优先的多媒体收藏管理工具。把散落在硬盘上的电子书、图片、音频、视频、游戏和模型文件整理成作品条目，用自定义标签和评分描述它们，并把评价导出成可分享的数据包。

## 当前阶段

Alpha 第一阶段：跑通「建条目 → 关联文件 → 打标签评分 → 检索」的最小链路。

## 技术栈

- 桌面容器：PyWebView
- 后端：Python 3.12 + FastAPI + Uvicorn
- 前端：Vue 3 + TypeScript + Vite
- 数据：SQLite + SQLAlchemy 2 + Alembic
- 测试：pytest + HTTPX + Playwright
- 打包：PyInstaller

## 目录结构

```
backend/     FastAPI 应用、领域模型、数据访问、适配器和后台任务
frontend/    Vue 3 + TypeScript + Vite 页面
desktop/     PyWebView 桌面启动器
tests/       接口、数据库和主流程测试
docs/        架构、分享包规范和协作约定
data/        运行时数据库与日志，不提交到仓库
```

## 本地启动

后端：

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

访问 http://127.0.0.1:8000/api/health ，应返回 `{"status":"ok"}`。

前端：

```powershell
cd frontend
npm install
npm run dev
```

桌面窗口（先构建前端）：

```powershell
cd frontend
npm run build
cd ..
python desktop/launcher.py
```

## 八人分工

| 成员 | 主线 | 主要目录 |
|---|---|---|
| 成员一 | 数据与存储 | `backend/app/db/`、`backend/migrations/` |
| 成员二 | 条目与资源 | `backend/app/api/`、`backend/app/application/` |
| 成员三（张亦弛） | 标签与评分 | `backend/app/application/` |
| 成员四 | 检索与展示 | `backend/app/application/`、`frontend/src/` |
| 成员五 | 分享包 | `backend/app/application/`、`docs/share-package-spec.md` |
| 成员六 | 界面与交互 | `frontend/src/` |
| 成员七 | 扩展与适配 | `backend/app/adapters/` |
| 成员八 | 质量与发布 | `tests/`、`.github/`、`desktop/` |

## 协作约定

- `main` 始终可运行，禁止直接推送。
- 分支命名：`feature/<模块>-<简述>`、`fix/<模块>-<简述>`、`docs/<文件名>`。
- 提交格式：`feat: 说明 (#12)`、`fix: 说明 (#13)`、`docs: 说明`。
- 每个 PR 关联一个 Issue，至少一名其他成员评审，统一 Squash merge。

详见 [docs/branching.md](docs/branching.md)。

## 文档

- [技术架构](docs/architecture.md)
- [分支与提交规范](docs/branching.md)
- [会议记录模板](docs/meetings/README.md)
