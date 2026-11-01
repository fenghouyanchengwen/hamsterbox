# 条目与资源接口契约

| 项目 | 内容 |
| --- | --- |
| 负责人 | 成员2：条目与资源 |
| 状态 | Alpha v0.1 草案，待成员1、成员4、成员6和成员8评审 |
| 更新日期 | 2026-10-31 |
| 适用范围 | 条目 CRUD、本地资源关联、资源状态检测和移出库 |

## 1. 已确认的边界

1. Alpha 阶段的 `resources` 表使用 `entry_id`，一个资源记录只属于一个条目。
2. 同一磁盘文件被多个条目引用的检测和提示属于 Beta，不在本契约实现。
3. 成员2负责条目写入、条目详情和资源接口；成员4负责 `GET /api/entries` 的列表、搜索、筛选、排序和分页。
4. Alpha 的“移出库”只修改数据库，不删除、移动或重命名磁盘文件。
5. 原始文件继续保留在用户原来的位置；数据库保存绝对路径及文件元数据。
6. 打开文件不提供 HTTP 业务接口，由 PyWebView JS 桥调用内部资源路径解析服务。
7. 条目类型使用领域模型中的英文稳定值：`game`、`book`、`video`、`audio`、`image`、`model`、`other`。

## 2. 分层责任

```text
HTTP 路由
  -> EntryService / ResourceService
      -> 仓储与数据库
      -> 文件类型适配器

PyWebView JS 桥
  -> ResourceService.resolve_path(resource_id)
      -> 受控地调用系统默认程序
```

路由只负责参数解析、调用应用服务和错误映射。应用服务负责业务校验和事务边界。路由不得直接执行 SQL，前端或 JS 桥不得把任意绝对路径交给系统命令。

## 3. 通用 HTTP 约定

### 3.1 前缀和媒体类型

- 所有路径以 `/api` 开头。
- 请求和响应使用 `application/json`。
- 时间使用 UTC ISO 8601，示例格式为 `2026-10-31T08:00:00Z`。
- ID 使用正整数；`share_id` 使用稳定 UUID，但本契约不允许客户端用 SQLite 自增 ID 代替 `share_id`。

### 3.2 错误响应

所有业务错误使用以下结构：

```json
{
  "code": "ENTRY_NOT_FOUND",
  "message": "条目不存在",
  "details": {
    "entry_id": 42
  }
}
```

错误码是前后端依赖的稳定标识，`message` 只用于展示，不能被前端用来判断分支。

| 状态码 | 使用场景 |
| --- | --- |
| 201 | 创建条目或资源成功 |
| 204 | 删除或解除关联成功，响应无正文 |
| 400 | 当前状态不允许操作 |
| 404 | 条目、资源或资源关联不存在 |
| 409 | 重复关联或其他资源状态冲突 |
| 422 | 请求字段校验失败 |
| 500 | 未预期的服务错误；不得把堆栈返回给客户端 |

本模块错误码：

| 错误码 | HTTP | 含义 |
| --- | ---: | --- |
| `ENTRY_NOT_FOUND` | 404 | 条目不存在 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `RESOURCE_LINK_NOT_FOUND` | 404 | 指定条目没有关联该资源 |
| `RESOURCE_FILE_MISSING` | 409 | 数据库记录存在，但磁盘文件不存在 |
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
  "cover_path": null
}
```

字段规则：

- `title` 必填，去除首尾空白后长度为 1 至 200。
- `type` 必填，只能是 `game`、`book`、`video`、`audio`、`image`、`model`、`other`。
- `description` 可为空，最大 20000 字符。
- `cover_path` 可为空；如果提供，后端必须按封面路径规则校验，不能把任意路径当作可信输入。

成功：`201 Created`

```json
{
  "id": 1,
  "share_id": "a19d1060-7288-4c86-a2e7-3340c7c58be1",
  "title": "示例游戏",
  "type": "game",
  "description": "一个测试条目",
  "cover_path": null,
  "created_at": "2026-10-31T08:00:00Z",
  "updated_at": "2026-10-31T08:00:00Z"
}
```

### 4.2 查询条目详情

```text
GET /api/entries/{entry_id}
```

成功：`200 OK`

响应使用 `EntryDetail`：

```json
{
  "id": 1,
  "share_id": "a19d1060-7288-4c86-a2e7-3340c7c58be1",
  "title": "示例游戏",
  "type": "game",
  "description": "一个测试条目",
  "cover_path": null,
  "created_at": "2026-10-31T08:00:00Z",
  "updated_at": "2026-10-31T08:00:00Z",
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

注意：响应不包含资源的本地绝对路径。

### 4.3 修改条目

```text
PATCH /api/entries/{entry_id}
```

请求字段全部可选，但至少应提供一个字段：

```json
{
  "title": "示例游戏 重制版",
  "description": "更新后的简介",
  "cover_path": null,
  "type": "game"
}
```

成功：`200 OK`，返回更新后的 `EntryRead`。不存在时返回 `ENTRY_NOT_FOUND`。

### 4.4 移出库

```text
DELETE /api/entries/{entry_id}
```

成功：`204 No Content`。

Alpha 行为：删除条目及其库内关联记录，不调用删除文件、移动文件或重命名文件的系统能力。实际是否级联删除资源数据库记录由成员1的迁移和 ORM 约束实现，但磁盘文件必须保留。

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

处理顺序必须是：

```text
规范化路径
-> 确认绝对路径
-> 确认存在且为普通文件
-> 读取文件名、扩展名、大小和修改时间
-> 识别文件类型
-> 检查当前条目是否已关联
-> 计算 SHA-256
-> 在一个事务中写入资源关联
```

规则：

- `path` 必须是绝对路径。
- 后端必须重新检查路径，不能信任前端或 JS 桥的校验结果。
- `file_name` 为空时使用路径的实际文件名；如果提供，必须与路径的文件名一致或由后端忽略并重新生成。
- Alpha 阶段只检查当前条目是否重复关联，不实现跨条目共享提示。

成功：`201 Created`，返回 `ResourceRead`。资源响应不得包含 `path`。

### 5.2 查询条目资源

```text
GET /api/entries/{entry_id}/resources
```

成功：`200 OK`

```json
{
  "items": [],
  "total": 0
}
```

该接口只返回指定条目的资源，不承担关键词、标签、评分、排序和分页检索职责。若条目不存在，返回 `ENTRY_NOT_FOUND`。

### 5.3 解除资源关联

```text
DELETE /api/entries/{entry_id}/resources/{resource_id}
```

成功：`204 No Content`。

解除关联不删除、不移动、不重命名磁盘文件。条目或资源不存在时分别返回 `ENTRY_NOT_FOUND` 或 `RESOURCE_LINK_NOT_FOUND`。

### 5.4 重新检测资源状态

```text
POST /api/resources/{resource_id}/recheck
```

成功：`200 OK`

```json
{
  "id": 10,
  "file_name": "example.mp4",
  "extension": ".mp4",
  "size_bytes": 123456,
  "mtime_ns": 1730000000000000000,
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "availability": "present",
  "changed": false
}
```

如果文件不存在，返回 `200 OK` 并将 `availability` 设置为 `missing`；这是资源状态，不是 HTTP 请求失败。若路径不可访问，返回 `RESOURCE_ACCESS_DENIED`。

## 6. 打开资源的 JS 桥边界

打开资源不新增 HTTP 路由。前端调用：

```text
window.pywebview.api.open_resource(resource_id)
```

桥接方法只接受 `resource_id`。内部调用成员2的应用服务：

```python
class ResourceService:
    def resolve_path(self, resource_id: int) -> Path: ...
    def open_resource(self, resource_id: int) -> None: ...
```

内部处理顺序：查询资源、确认路径存在、确认是普通文件、确认可访问，然后交给受控的系统能力适配器调用默认程序。前端不能传入任意路径，后端不能使用 `shell=True` 拼接命令。

桥接失败时使用与 HTTP 相同的错误码语义，例如 `RESOURCE_NOT_FOUND`、`RESOURCE_FILE_MISSING` 和 `RESOURCE_OPEN_FAILED`。

## 7. 应用服务建议接口

```python
class EntryService:
    def create_entry(self, payload: EntryCreate) -> EntryRead: ...
    def get_entry(self, entry_id: int) -> EntryDetail: ...
    def update_entry(self, entry_id: int, payload: EntryUpdate) -> EntryRead: ...
    def remove_entry(self, entry_id: int) -> None: ...


class ResourceService:
    def list_resources(self, entry_id: int) -> ResourcePage: ...
    def attach_resource(self, entry_id: int, payload: ResourceCreate) -> ResourceRead: ...
    def detach_resource(self, entry_id: int, resource_id: int) -> None: ...
    def recheck_resource(self, resource_id: int) -> ResourceStatus: ...
    def resolve_path(self, resource_id: int) -> Path: ...
```

应用服务抛出领域异常，API 层再映射为 HTTP 错误。应用服务不能导入 FastAPI 的 `Request` 或 `HTTPException`。

## 8. 成员2不负责的接口

以下接口由其他成员负责，成员2不能在自己的分支中重复实现：

- `GET /api/entries`：成员4负责搜索、筛选、排序和分页。
- `/api/tags`：成员3负责标签。
- `/api/entries/{entry_id}/ratings`：成员3负责评分。
- `/api/share/*`：成员5负责分享包。
- `/api/resources/delete`：Beta 阶段安全删除，由后续任务负责。

## 9. 测试验收清单

- 创建正常条目成功。
- 标题为空、类型非法时返回 422。
- 查询不存在条目返回 404 和 `ENTRY_NOT_FOUND`。
- 修改条目成功，未提供的字段保持不变。
- 一个条目可以关联多个文件。
- 关联不存在路径、目录或相对路径时返回明确错误。
- 当前条目重复关联同一文件时返回 409。
- 资源响应不泄露绝对路径。
- 文件被外部删除后重新检测得到 `availability=missing`。
- 解除关联和移出库都不删除磁盘文件。
- 打开资源只接收 `resource_id`，路径由后端解析。

## 10. 分支协作备注

- `origin/feature/member5-share-package-spec` 的示例曾把条目类型改成中文值；这与共享领域模型的英文枚举冲突。成员2接口继续使用英文稳定值，待成员5统一分享包规范后再联调。
- `origin/feature/tag-rating` 与当前 `main` 指向同一份接口文档提交，没有需要合并的成员2实现。
- `origin/扩展与适配` 目前没有成员2可直接复用的资源服务代码；Adapter 只通过约定接口被调用。
