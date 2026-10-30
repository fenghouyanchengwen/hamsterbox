# API 接口说明

## 统一约定

- 前缀统一为 `/api`。
- 请求与响应均为 `application/json`，分享包预览除外。
- 分页响应格式：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 50
}
```

- 错误响应格式：

```json
{
  "code": "RATING_OUT_OF_RANGE",
  "message": "评分必须是 1 到 5 的整数",
  "details": { "field": "rating" }
}
```

| HTTP 状态 | 含义 |
|---|---|
| 400 | 请求格式或状态不允许 |
| 404 | 条目、资源或标签不存在 |
| 409 | 唯一约束冲突，例如标签重名、标签仍被引用 |
| 422 | 字段校验失败，例如颜色格式或评分越界 |

## 系统

| 方法 | 路径 | 用途 | 负责人 |
|---|---|---|---|
| GET | `/api/health` | 健康检查，返回 `{"status":"ok"}` | 成员八 |
| GET | `/api/version` | 返回应用版本 | 成员八 |

## 条目

| 方法 | 路径 | 用途 | 负责人 |
|---|---|---|---|
| GET | `/api/entries` | 列表、检索、筛选与分页 | 成员二、四 |
| POST | `/api/entries` | 新建条目 | 成员二 |
| GET | `/api/entries/{entry_id}` | 条目详情 | 成员二 |
| PATCH | `/api/entries/{entry_id}` | 编辑标题、类型、简介、封面 | 成员二 |
| DELETE | `/api/entries/{entry_id}` | 移出库，不删除磁盘文件 | 成员二 |

`GET /api/entries` 查询参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `q` | string | 标题与简介关键词 |
| `type` | string | 条目类型，可重复 |
| `tag_id` | int | 标签 ID，可重复 |
| `tag_mode` | `and` / `or` | 多标签匹配方式，默认 `and` |
| `rating_min` / `rating_max` | int | 评分区间，1 至 5 |
| `sort` | string | `updated_desc`、`title_asc`、`rating_desc` |
| `page` / `page_size` | int | 分页参数，默认 1 与 50 |

## 资源

| 方法 | 路径 | 用途 | 负责人 |
|---|---|---|---|
| POST | `/api/entries/{entry_id}/resources` | 关联一个本地文件 | 成员二 |
| DELETE | `/api/entries/{entry_id}/resources/{resource_id}` | 解除关联，不删除文件 | 成员二 |
| POST | `/api/resources/{resource_id}/recheck` | 重新检测存在性并刷新哈希 | 成员二、七 |

关联请求体：

```json
{
  "path": "D:\\Media\\example.mp4",
  "file_name": "example.mp4"
}
```

`path` 只能来自原生文件选择器的返回值，后端保存前必须校验存在性与绝对路径。

打开文件不通过 HTTP，由前端调用 JS 桥 `open_resource(resource_id)`，后端根据 ID 解析真实路径。

## 标签

| 方法 | 路径 | 用途 | 负责人 |
|---|---|---|---|
| GET | `/api/tags` | 标签列表 | 成员三 |
| POST | `/api/tags` | 新建标签 | 成员三 |
| PATCH | `/api/tags/{tag_id}` | 修改名称、颜色、是否启用评分 | 成员三 |
| DELETE | `/api/tags/{tag_id}` | 删除标签；仍被引用时返回 409 | 成员三 |

创建与修改请求体：

```json
{
  "name": "剧情",
  "color": "#5B8FF9",
  "rating_enabled": true
}
```

## 评分

| 方法 | 路径 | 用途 | 负责人 |
|---|---|---|---|
| GET | `/api/entries/{entry_id}/ratings` | 读取条目的全部标签评分 | 成员三 |
| PUT | `/api/entries/{entry_id}/ratings/{tag_id}` | 写入或更新评分与评价 | 成员三 |
| DELETE | `/api/entries/{entry_id}/ratings/{tag_id}` | 清除评分与评价 | 成员三 |

写入请求体：

```json
{
  "rating": 5,
  "review": "节奏很好"
}
```

规则：

- `rating` 必须是 1 至 5 的整数。
- 标签 `rating_enabled=false` 时，`rating` 必须为 `null`。
- 同一 `entry_id` 与 `tag_id` 只能有一条记录。

## 分享包

| 方法 | 路径 | 用途 | 负责人 |
|---|---|---|---|
| POST | `/api/share/export` | 导出 `.hbox` 分享包 | 成员五 |
| POST | `/api/share/preview` | 上传并预览分享包 | 成员五 |
| POST | `/api/share/import` | 按预览结果执行导入 | 成员五 |

导出请求体：

```json
{
  "entry_ids": [1, 2, 3],
  "include_covers": true
}
```

导入分两步：`preview` 返回条目、冲突与缺失资源，用户确认后再调用 `import`。导入不写入数据库，直到用户确认。

分享包格式以 `docs/share-package-spec.md` 为准。

## Beta 阶段接口

以下接口不在 Alpha 第一阶段实现：

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/resources/delete` | 移入系统回收站 |
| POST | `/api/entries/{entry_id}/resources/batch` | 文件夹批量导入 |
| GET | `/api/stats` | 类型、标签与空间统计 |
| POST | `/api/importers/steam/preview` | Steam 库导入 |
| POST | `/api/importers/gog/preview` | GOG 库导入 |
