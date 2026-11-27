# 条目与资源接口契约

| 项目 | 内容 |
| --- | --- |
| 负责人 | 成员2：条目与资源 |
| 状态 | v0.3.0（已对齐标签评分契约 v1） |
| 更新日期 | 2026-11-27 |
| 适用范围 | 条目 CRUD、整体评价与生命周期、本地资源关联、状态重检 |

## 1. 已确认的边界

1. `resources` 表使用 `entry_id` 外键（`ON DELETE CASCADE`），一条资源记录关联一个条目；同一磁盘文件可被多个条目分别关联。
2. 成员2负责条目写入、条目详情、临时派生条目生命周期服务、资源关联/重检；成员4负责 `GET /api/entries` 的列表、搜索、筛选、排序和分页。
3. “移出库”（`DELETE /api/entries/{entry_id}`）和“解除关联”（`DELETE /api/entries/{entry_id}/resources/{resource_id}`）只修改数据库，不删除、移动或重命名磁盘文件。
4. 打开文件不提供 HTTP 业务接口，由 PyWebView JS 桥调用 `ResourceService.open_resource(resource_id)`。
5. 条目类型使用领域模型中的英文稳定值：`game`、`book`、`video`、`audio`、`image`、`model`、`other`。

## 2. 分层责任

```text
HTTP 路由
  -> EntryService / ResourceService
      -> 仓储与数据库
      -> 文件类型识别器（TypeRegistry）

PyWebView JS 桥
  -> ResourceService.open_resource(resource_id)
      -> ResourceService.resolve_path(resource_id)
      -> 受控地调用系统默认程序（SystemDefaultOpener）
```

路由只负责参数解析、调用应用服务和错误映射。应用服务负责业务校验和事务边界。路由不得直接执行 SQL，前端或 JS 桥不得把任意绝对路径交给打开或删除命令。

## 3. 通用 HTTP 约定

### 3.1 前缀和媒体类型

- 所有路径以 `/api` 开头。
- 请求和响应使用 `application/json`。
- 时间统一按 UTC 存储，公开响应统一输出带 UTC 时区的 ISO 8601 字符串（如 `2026-11-27T08:00:00Z`）。
- ID 使用正整数；`share_id` 使用稳定 UUID，不允许客户端用 SQLite 自增 ID 代替 `share_id`。

### 3.2 错误响应

所有业务错误使用以下结构：

```json
{
  "code": "ENTRY_NOT_FOUND",
  "message": "条目 42 不存在",
  "details": {
    "entry_id": 42
  }
}
```

错误码是前后端依赖的稳定标识，`message` 只用于展示，不能被前端用来判断分支。

| 错误码 | HTTP | 含义 |
| --- | ---: | --- |
| `ENTRY_NOT_FOUND` | 404 | 条目不存在 |
| `ENTRY_REVIEW_TOO_LONG` | 422 | 条目整体评价超过 10000 字符 |
| `ENTRY_LIFECYCLE_INVALID` | 400 | 条目生命周期状态不允许当前操作（如将正式库条目作为临时条目清理） |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `RESOURCE_LINK_NOT_FOUND` | 404 | 指定条目没有关联该资源 |
| `RESOURCE_FILE_MISSING` | 409 | 数据库记录或请求路径对应的磁盘文件不存在 |
| `RESOURCE_NOT_FILE` | 422 | 路径存在但不是普通文件 |
| `RESOURCE_PATH_NOT_ABSOLUTE` | 422 | 路径不是绝对路径 |
| `RESOURCE_ACCESS_DENIED` | 409 | 当前进程无法访问文件 |
| `RESOURCE_ALREADY_LINKED` | 409 | 该条目已经关联此文件 |
| `RESOURCE_OPEN_FAILED` | 409 | 系统默认程序打开失败 |

## 4. 条目接口

### 4.1 新建条目

```text
POST /api/entries
```

请求：

```json
{
  "title": "示例游戏",
  "type": "game",
  "description": "一个测试条目",
  "review": "整体完成度很高",
  "cover_path": null
}
```

字段规则：

- `title` 必填，去除首尾空白后长度为 1 至 200。
- `type` 必填，只能是 `game`、`book`、`video`、`audio`、`image`、`model`、`other`。
- `description` 可为空，最大 20000 字符。
- `review` 可为空，保存条目唯一的一份整体评价文字，最大 10000 字符；超出时返回 `422 ENTRY_REVIEW_TOO_LONG`。
- `cover_path` 可为空；如果提供非空字符串，后端校验其必须为可访问的本地绝对路径且为普通文件，规范化后仅保存在数据库内部使用，**不在 HTTP 响应中回传本地绝对路径**。
- 普通创建接口固定产生 `lifecycle_state="library"`，不向客户端开放创建 `temporary` 条目。

成功：`201 Created`

```json
{
  "id": 1,
  "share_id": "a19d1060-7288-4c86-a2e7-3340c7c58be1",
  "title": "示例游戏",
  "type": "game",
  "description": "一个测试条目",
  "review": "整体完成度很高",
  "lifecycle_state": "library",
  "has_cover": false,
  "created_at": "2026-11-27T08:00:00Z",
  "updated_at": "2026-11-27T08:00:00Z"
}
```

### 4.2 查询条目详情

```text
GET /api/entries/{entry_id}
```

成功：`200 OK`，返回 `EntryDetail`（在 `EntryRead` 基础上包含 `resources` 列表，条目与资源均不暴露本地绝对路径）：

```json
{
  "id": 1,
  "share_id": "a19d1060-7288-4c86-a2e7-3340c7c58be1",
  "title": "示例游戏",
  "type": "game",
  "description": "一个测试条目",
  "review": "整体完成度很高",
  "lifecycle_state": "library",
  "has_cover": false,
  "created_at": "2026-11-27T08:00:00Z",
  "updated_at": "2026-11-27T08:00:00Z",
  "resources": [
    {
      "id": 10,
      "share_id": "c73ef2e8-dcf8-4d3b-8e44-36cd95c1e4d8",
      "entry_id": 1,
      "file_name": "example_game.exe",
      "extension": ".exe",
      "size_bytes": 123456,
      "mtime_ns": 1730000000000000000,
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "availability": "present"
    }
  ]
}
```

### 4.3 修改条目

```text
PATCH /api/entries/{entry_id}
```

请求字段全部可选，但**至少应提供一个字段**（空对象 `{}` 返回 `422`）；非空必填字段 `title` 与 `type` 不允许显式置为 `null`；清空简介、评价或封面可显式传 `null`：

```json
{
  "title": "示例游戏 重制版",
  "description": "更新后的简介",
  "review": "二周目补充评价",
  "cover_path": null,
  "type": "game"
}
```

成功：`200 OK`，返回更新后的 `EntryRead`。不存在时返回 `404 ENTRY_NOT_FOUND`。

### 4.4 移出库

```text
DELETE /api/entries/{entry_id}
```

成功：`204 No Content`。级联删除数据库中的条目、资源关联与条目标签关系记录，磁盘上的原始文件原样保留。

### 4.5 临时派生条目内部服务（供分享模块调用）

部分资源分享时，不在 HTTP 层开放普通用户创建 `temporary` 条目，而是由分享应用服务调用 `EntryService`：

- `create_temporary_entry(payload, source_resource_ids=...)`：创建 `lifecycle_state="temporary"` 的隐藏条目并复制所选资源引用（不改动原条目；检索接口自动过滤 `temporary`）。
- `promote_temporary_entry(entry_id, review=...)`：用户确认保留时将 `temporary` 转为 `library`。
- `discard_temporary_entry(entry_id)`：分享取消、失败或选择删除时清理临时条目；若传入 `library` 条目将拒绝并抛出 `InvalidEntryLifecycleError`。

## 5. 资源接口

### 5.1 关联本地文件

```text
POST /api/entries/{entry_id}/resources
```

请求：

```json
{
  "path": "D:\\Media\\example.mp4",
  "file_name": "example.mp4"
}
```

处理顺序：

```text
规范化路径
-> 确认绝对路径
-> 确认存在且为普通文件
-> 检查当前条目是否已关联
-> 计算 SHA-256
-> 调用 TypeRegistry 识别文件类型（异常安全降级为 other）
-> 写入资源关联
-> 若当前条目 type 为 other 且识别出具体媒体类型，则自动补齐条目 type（不覆盖用户显式设置的其他作品类型）
```

成功：`201 Created`，返回 `ResourceRead`（不包含 `path`）。

### 5.2 查询条目资源

```text
GET /api/entries/{entry_id}/resources
```

成功：`200 OK`，返回 `{"items": [...], "total": 0}`。若条目不存在，返回 `404 ENTRY_NOT_FOUND`。

### 5.3 解除资源关联

```text
DELETE /api/entries/{entry_id}/resources/{resource_id}
```

成功：`204 No Content`。只移除数据库关联记录，不修改磁盘文件。

### 5.4 重新检测资源状态

```text
POST /api/resources/{resource_id}/recheck
```

成功：`200 OK`，返回带 `changed: bool` 的 `ResourceRecheck`。文件不存在时返回 `200 OK` 且 `availability="missing"`。

## 6. 打开资源的 JS 桥边界

前端只调用 `window.pywebview.api.open_resource(resource_id)`，桥接层只接受整数 `resource_id` 并委托 `ResourceService.open_resource(resource_id, confirm_open=...)`。`.exe`、`.bat`、`.cmd`、`.lnk` 由原生确认对话框拦截确认后才启动默认程序。
