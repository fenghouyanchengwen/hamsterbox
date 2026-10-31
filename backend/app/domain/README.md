# 领域模型说明

## 职责

定义跨层共享的 Pydantic 模型、枚举和分页类型。领域层不访问数据库，也不依赖 FastAPI。

负责人：成员一至五共同确认，成员一维护基础类型。

## 枚举

```python
class EntryType(str, Enum):
    GAME = "game"
    BOOK = "book"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    MODEL = "model"
    OTHER = "other"
```

## 条目

| 模型 | 字段 |
|---|---|
| `EntryCreate` | `title`、`type`、`description?`、`cover_path?` |
| `EntryUpdate` | 以上字段全部可选 |
| `EntryRead` | `id`、`share_id`、`title`、`type`、`description`、`cover_path`、`created_at`、`updated_at` |
| `EntryQuery` | `q?`、`type?`、`tag_ids`、`tag_mode`、`rating_min?`、`rating_max?`、`sort`、`page`、`page_size` |

校验：

- `title` 去空格后 1 至 200 字符。
- `description` 最大 20000 字符。
- `type` 必须属于 `EntryType`。

## 资源

| 模型 | 字段 |
|---|---|
| `ResourceCreate` | `path`、`file_name?` |
| `ResourceRead` | `id`、`share_id`、`entry_id`、`file_name`、`extension`、`size_bytes`、`mtime_ns`、`sha256`、`availability` |

`ResourceRead` 不返回本地绝对路径，路径只在后端内部使用。

`ResourceList` 用于资源列表接口，包含 `items` 和 `total`；`ResourceRecheck` 在 `ResourceRead` 基础上增加 `changed`，用于说明重新检测是否发现文件元数据变化。

## 标签与评分

| 模型 | 字段 |
|---|---|
| `TagCreate` | `name`、`color?`、`rating_enabled` |
| `TagUpdate` | 以上字段全部可选 |
| `TagRead` | `id`、`share_id`、`name`、`color`、`rating_enabled` |
| `RatingUpsert` | `rating?`、`review?` |
| `EntryTagRead` | `tag_id`、`name`、`color`、`rating_enabled`、`rating`、`review` |

校验：

- `name` 去空格后 1 至 32 字符。
- `color` 为 `null` 或匹配 `^#[0-9A-Fa-f]{6}$`。
- `rating` 为 `null` 或 1 至 5 的整数。
- `rating_enabled=false` 时 `rating` 必须为 `null`。
- `review` 最大 10000 字符。

## 分享包

| 模型 | 字段 |
|---|---|
| `ShareExportRequest` | `entry_ids`、`include_covers` |
| `ShareExportResult` | `package_id`、`file_name`、`entry_count` |
| `SharePreview` | `preview_id`、`entries`、`conflicts`、`missing_resources` |
| `ImportSelection` | `preview_id`、`entry_share_ids` |

## 分页

```python
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
```

## 命名约定

- 分享包与 API 统一使用 `rating_enabled`、`rating`、`review`、`share_id`。
- 时间字段统一以 `_at` 结尾，值为 UTC。
- 金额、大小等计数统一带单位后缀，例如 `size_bytes`。
