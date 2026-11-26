# 数据层说明

| 项目 | 内容 |
|---|---|
| 用途 | 维护 SQLAlchemy 2 模型、Session、仓储、Alembic 迁移与备份 |
| 负责人 | 成员一：数据与存储 |
| 最后更新 | 2026-11-01 |

数据库只保存元数据、绝对路径和哈希，不保存原始媒体内容。

## 迁移链

本目录的结构以 Alembic 迁移为准，`app/db/models.py` 只描述当前 head。

| 版本 | 内容 | 状态 |
|---|---|---|
| `0001_alpha1_initial_schema` | 旧契约基线：entries、resources、tags、entry_tags、app_settings | 历史版本 |
| `0002_tag_category_review` | 标签分类与条目评价契约：tag_categories、entries.review/lifecycle_state、评分 1 至 10 | 已冻结（PR #22），当前 head |

```powershell
# 在 backend 目录执行
alembic upgrade head                          # 升到最新（当前 = 0002）
alembic upgrade 0001_alpha1_initial_schema    # 只用旧基线，供排查历史库
alembic downgrade base                        # 清空
alembic current
```

`app/db/session.py:init_db()` 在应用启动时执行 `upgrade head`，因此本地不需要手工迁移。
缺少迁移脚本的打包形态才会回退到 `create_all`。

## 表结构（head = 0002）

### entries

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `share_id` | TEXT | UUID，唯一，分享包使用 |
| `title` | TEXT | 非空，索引 |
| `type` | TEXT | 非空，取值为 game、book、video、audio、image、model、other |
| `description` | TEXT | 可空 |
| `review` | TEXT | 可空，条目整体评价，最多 10000 字符（应用层校验） |
| `lifecycle_state` | TEXT | `library` 或 `temporary`，默认 `library` |
| `cover_path` | TEXT | 可空 |
| `created_at` | TEXT | UTC ISO 8601 |
| `updated_at` | TEXT | UTC ISO 8601 |

### resources

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `share_id` | TEXT | UUID，唯一 |
| `entry_id` | INTEGER | 外键 entries.id，`ON DELETE CASCADE`，索引 |
| `path` | TEXT | 非空，绝对路径 |
| `file_name` | TEXT | 非空 |
| `extension` | TEXT | 小写，含点号 |
| `size_bytes` | INTEGER | 可空 |
| `mtime_ns` | INTEGER | 可空 |
| `sha256` | TEXT | 可空，64 位小写十六进制，索引 |
| `availability` | TEXT | present 或 missing |
| `created_at` | TEXT | UTC |

### tag_categories

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `name` | TEXT | 非空，去空格后 1 至 32 字符，NOCASE 唯一 |
| `color` | TEXT | 可空，本地使用，匹配 `^#[0-9A-Fa-f]{6}$` |
| `sort_order` | INTEGER | 非空，默认 0，按升序显示 |
| `system_key` | TEXT | 可空，唯一；系统「未分类标签」为 `uncategorized` |
| `created_at` | TEXT | UTC |
| `updated_at` | TEXT | UTC |

### tags

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `category_id` | INTEGER | 外键 tag_categories.id，`ON DELETE RESTRICT`，索引 |
| `name` | TEXT | 非空，去空格后 1 至 32 字符，保留原始大小写 |
| `normalized_name` | TEXT | 非空，由 `casefold()` 生成 |
| `created_at` | TEXT | UTC |
| `updated_at` | TEXT | UTC |

唯一约束为 `(category_id, normalized_name)`：同一分类内不重名，跨分类允许同名。
标签不保存 `share_id`、颜色或评分开关。

### entry_tags

| 字段 | 类型 | 约束 |
|---|---|---|
| `entry_id` | INTEGER | 外键 entries.id，`ON DELETE CASCADE` |
| `tag_id` | INTEGER | 外键 tags.id，`ON DELETE RESTRICT`，索引 |
| `rating` | INTEGER | 可空，1 至 10 |
| `created_at` | TEXT | UTC |
| `updated_at` | TEXT | UTC |

主键为 `(entry_id, tag_id)`。删除条目会级联删除其关系；删除仍被引用的标签由数据库
拒绝（RESTRICT），应用服务应先用 `count_by_tag(tag_id)` 判断并返回 409，而不是级联删除。

### app_settings

| 字段 | 类型 | 约束 |
|---|---|---|
| `key` | TEXT | 主键 |
| `value` | TEXT | 非空 |
| `updated_at` | TEXT | UTC |

## 索引

| 表 | 索引 | 用途 |
|---|---|---|
| entries | `ix_entries_title` | 标题排序与搜索 |
| resources | `ix_resources_entry_id` | 条目详情 |
| resources | `ix_resources_sha256` | 分享包匹配 |
| entry_tags | `ix_entry_tags_tag_id` | 按标签筛选 |
| tags | `ix_tags_category_id` | 分类下标签列表 |
| tags | `uq_tags_category_normalized_name` | 分类内重名校验 |
| tag_categories | `uq_tag_categories_name` | 分类重名校验（NOCASE） |

关键词搜索在 FTS5 可用时可另建 `entries_fts`；Alpha 阶段先用 `LIKE` 并记录性能基线。

## SQLite 配置

- 每个连接建立后执行：`foreign_keys=ON`、`journal_mode=WAL`、`synchronous=NORMAL`、
  `busy_timeout=5000`。
- 连接参数为 `check_same_thread=False`，由 Session 管理并发。
- 数据库路径默认为 `data/library.db`，可用 `HAMSTERBOX_DB_PATH` 覆盖；
  URL 可用 `HAMSTERBOX_DB_URL` 覆盖（测试与 CI 使用）。
- 迁移期间由 `migrations/env.py` 临时关闭外键，迁移后执行 `PRAGMA foreign_key_check`
  并在不通过时回滚。

## 仓储

| 文件 | 负责 |
|---|---|
| `entry_repository.py` | 条目增删改查（成员二维护） |
| `resource_repository.py` | 资源增删改查（成员二维护） |
| `tag_category_repository.py` | 分类增删改查、按名称/系统键查找、分类下标签计数 |
| `tag_repository.py` | 标签增删改查、按分类和名称查找、重命名 |
| `entry_tag_repository.py` | 条目标签关系与评分的幂等写入、查询、计数 |
| `app_setting_repository.py` | 设置项读写 |
| `backup.py` | 在线备份、保留策略、完整性/外键校验 |

本分支新增的仓储**不提交事务**，只调用 `flush()`，由应用服务决定提交时机
（见 `backend/app/application/README.md` 的事务规则）。成员二已合并的条目和资源仓储
仍保留内部 `commit()`，迁移到统一规则属于后续重构，不在本次改动范围内。

返回类型是 `app/db/records.py` 中的只读 dataclass（含 `StoredResource`），应用服务再转换成
领域模型。数据层只允许引用 `app.domain` 的只读模型，**不得**反向依赖 `app.application`
或 `app.api`；`StoredResource` 曾在 `application/ports.py` 定义并被仓储导入，已按
Issue #27 移到 `records.py`，`ports.py` 反过来从这里导入。

## 备份

```python
from app.db.backup import create_backup, verify_backup

target = create_backup("data/library.db", "data/backups")
assert verify_backup(target)
```

- 备份前执行 `PRAGMA wal_checkpoint(TRUNCATE)`，再走 SQLite 在线备份接口。
- 文件名 `library-YYYYMMDD-HHMMSS.db`，默认保留最近 10 份，同一秒内自动加序号。
- 恢复后先 `PRAGMA foreign_key_check`，通过后再允许应用启动。

## 迁移

```powershell
cd backend
alembic revision -m "add xxx"          # 手写迁移，禁止把 autogenerate 结果直接提交
alembic upgrade head
```

- 已提交的迁移不得修改，只能新增。
- 每个迁移必须能在空库上完整执行，并能在 `downgrade` 后回到上一版本。
- SQLite 删除列或改约束必须走「建新表 → 复制 → 重命名」。
- `alembic.ini` 必须保持纯 ASCII（Windows 下 configparser 按系统默认编码读取）。

## 契约来源

表结构以 `docs/tag-rating-contract.md`（PR #22 已冻结）为准；字段或取值变更先改契约，
再新增迁移，不在已合并的迁移上直接修改。
