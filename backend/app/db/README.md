# 数据层说明

## 职责

维护 SQLAlchemy 2 模型、Session、仓储和 Alembic 迁移。数据库只保存元数据、绝对路径和哈希，不保存原始媒体内容。

负责人：成员一。

## 表结构

### entries

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `share_id` | TEXT | UUID，唯一，分享包使用 |
| `title` | TEXT | 非空 |
| `type` | TEXT | 非空，取值为 game、book、video、audio、image、model、other |
| `description` | TEXT | 可空 |
| `review` | TEXT | 可空，最多 10000 字符 |
| `lifecycle_state` | TEXT | `library` 或 `temporary`，默认 `library` |
| `cover_path` | TEXT | 可空 |
| `created_at` | TEXT | UTC ISO 8601 |
| `updated_at` | TEXT | UTC ISO 8601 |

### resources

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `share_id` | TEXT | UUID，唯一 |
| `entry_id` | INTEGER | 外键 entries.id，级联删除 |
| `path` | TEXT | 非空，绝对路径 |
| `file_name` | TEXT | 非空 |
| `extension` | TEXT | 小写，含点号 |
| `size_bytes` | INTEGER | 可空 |
| `mtime_ns` | INTEGER | 可空 |
| `sha256` | TEXT | 可空，64 位小写十六进制 |
| `availability` | TEXT | present 或 missing |
| `created_at` | TEXT | UTC |

### tag_categories

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `name` | TEXT | 非空，去空格后 1 至 32 字符，大小写不敏感唯一 |
| `color` | TEXT | 可空，本地使用，匹配 `^#[0-9A-Fa-f]{6}$` |
| `sort_order` | INTEGER | 非空，默认按升序显示 |
| `system_key` | TEXT | 可空，唯一；系统“未分类标签”为 `uncategorized` |
| `created_at` | TEXT | UTC |
| `updated_at` | TEXT | UTC |

### tags

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `category_id` | INTEGER | 外键 tag_categories.id |
| `name` | TEXT | 非空，去空格后 1 至 32 字符 |
| `normalized_name` | TEXT | 非空，由 `casefold()` 生成 |
| `created_at` | TEXT | UTC |
| `updated_at` | TEXT | UTC |

唯一约束为 `(category_id, normalized_name)`。标签不保存 `share_id`、颜色或评分开关。

### entry_tags

| 字段 | 类型 | 约束 |
|---|---|---|
| `entry_id` | INTEGER | 外键 entries.id，级联删除 |
| `tag_id` | INTEGER | 外键 tags.id，级联删除 |
| `rating` | INTEGER | 可空，1 至 10 |
| `created_at` | TEXT | UTC |
| `updated_at` | TEXT | UTC |

主键为 `(entry_id, tag_id)`。

### app_settings

| 字段 | 类型 | 约束 |
|---|---|---|
| `key` | TEXT | 主键 |
| `value` | TEXT | 非空 |
| `updated_at` | TEXT | UTC |

## 索引

| 表 | 索引 | 用途 |
|---|---|---|
| entries | `title` | 标题排序与搜索 |
| resources | `entry_id` | 条目详情 |
| resources | `sha256` | 分享包匹配 |
| entry_tags | `tag_id` | 按标签筛选 |
| tags | `name` | 重名校验 |

关键词搜索可以在 FTS5 可用时建立 `entries_fts`，否则先使用 `LIKE` 并记录性能基线。

## SQLite 配置

- 启动时执行 `PRAGMA foreign_keys = ON`。
- 使用 WAL 模式。
- 连接设置为 `check_same_thread=False`，由 Session 管理并发。
- 事务边界在应用服务层开启和提交。

## 迁移

```powershell
alembic revision --autogenerate -m "init schema v1"
alembic upgrade head
```

- 已提交的迁移不得修改，只能新增。
- 每个迁移必须可在空库上完整执行。
- 迁移失败不得静默破坏已有库。

## 备份

- 备份文件放在 `data/backups/`。
- 备份前执行 WAL checkpoint。
- 恢复后运行外键一致性检查。
