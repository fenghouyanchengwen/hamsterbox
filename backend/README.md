# 后端模块说明

## 职责

后端在 `127.0.0.1` 上提供 HTTP/JSON API，承载条目、资源、标签、评分、检索和分享包的业务逻辑，并管理 SQLite 数据、事务与迁移。

后端不作为独立服务对外暴露，只服务本机的 PyWebView 窗口。

## 分层与边界

| 目录 | 职责 | 不做什么 |
|---|---|---|
| `app/api/` | 路由、参数解析、依赖注入、HTTP 错误映射 | 不写业务判断和 SQL |
| `app/application/` | 用例编排、状态校验、事务边界 | 不直接依赖 FastAPI 的 Request |
| `app/domain/` | Pydantic 模型、枚举、共享类型 | 不访问数据库 |
| `app/db/` | SQLAlchemy 模型、Session、仓储、迁移 | 不处理 JSON 响应 |
| `app/adapters/` | 文件类型识别与系统能力适配 | 不实现条目业务 |
| `app/workers/` | 哈希、扫描、导入等后台任务 | 不阻塞请求线程 |

调用方向固定为：

```
api  →  application  →  db
                ↘  adapters
                ↘  workers
```

## 启动方式

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/health`

## 接口总览

完整端点、请求体、响应体和错误码见 [app/api/README.md](app/api/README.md)。

业务流程与方法签名见 [app/application/README.md](app/application/README.md)。

## 共享约定

- 所有时间以 UTC 存储，界面按本地时区显示。
- 数据库只存元数据和绝对路径，不存原始媒体文件。
- 分享包不包含本地路径、原始文件或数据库主键。
- 评分为整数 1 至 5，未开启评分的标签不允许写入分数。
- 所有查询使用参数绑定，禁止拼接用户输入生成 SQL。

## 成员分工

| 成员 | 负责目录 |
|---|---|
| 成员一 | `app/db/`、`migrations/` |
| 成员二 | `app/api/`、`app/application/` 的条目与资源部分 |
| 成员三 | `app/application/` 的标签与评分部分 |
| 成员四 | 检索查询与分页参数 |
| 成员五 | 分享包导出、预览与导入 |
| 成员七 | `app/adapters/`、`app/workers/` |
| 成员八 | 启动、健康检查、测试与打包 |
