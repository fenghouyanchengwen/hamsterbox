# 成员一：数据与存储交接说明

| 项目 | 内容 |
|---|---|
| 用途 | 记录数据层的交付内容、跨成员依赖与后续顺序 |
| 负责人 | 成员一：数据与存储 |
| 状态 | Alpha 第一阶段数据层已完成，等待评审（已 rebase 到 main；契约 PR #22 已合并） |
| 最后更新 | 2026-11-01 |
| 分支 | `feature/db-alpha1-schema` |

## 1. 职责边界

成员一负责：

- SQLAlchemy 2 模型、Session 与连接配置；
- Alembic 迁移的初始化与维护；
- 条目、资源、标签、条目标签关系、设置项的仓储；
- 备份与数据库一致性校验。

成员一不负责：

- HTTP 路由与请求参数解析（成员二、三、四、五）；
- 应用服务的业务校验与错误映射（成员二、三）；
- 前端交互与展示（成员六）；
- 打包、启动器与 CI 流水线（成员八）。

## 2. 已完成

- 初始化 Alembic：`backend/alembic.ini`、`backend/migrations/env.py`、
  `script.py.mako`、`versions/`。
- `0001_alpha1_initial_schema`：旧契约基线，含 entries、resources、tags、
  entry_tags、app_settings 与全部索引、CHECK 约束。
- `0002_tag_category_review`：标签分类与条目评价契约（PR #22 已冻结），含 tag_categories、
  系统「未分类标签」、`entries.review`、`entries.lifecycle_state`、评分 1 至 10、
  tags 结构改造。
- 两个迁移都支持 `downgrade`，且都验证过空库完整执行与带数据升级。
- `session.py`：统一设置 `foreign_keys=ON`、`journal_mode=WAL`、`synchronous=NORMAL`、
  `busy_timeout=5000`；`init_db()` 走 `alembic upgrade head`。
- 数据库地址支持 `HAMSTERBOX_DB_PATH` / `HAMSTERBOX_DB_URL` 覆盖，测试和 CI 不再依赖
  真实用户库。
- 新增仓储：`tag_category_repository`、`tag_repository`、`entry_tag_repository`、
  `app_setting_repository`；返回 `records.py` 中的只读 dataclass。
- 新增 `backup.py`：在线备份、WAL checkpoint、保留最近 10 份、完整性与外键校验。
- 新增 50 个数据层测试，覆盖迁移链、级联删除、唯一约束、评分边界、仓储 CRUD 和备份；
  全量测试 81 项通过。

## 3. 跨成员协调事项

### 成员二：条目与资源

- 迁移已落地，`resources.entry_id` 的外键为 `ON DELETE CASCADE`，删除条目会一并删除
  资源记录和条目标签关系，磁盘文件不动。请补一次仓储与级联删除回归测试。
- `share_id` 已有唯一约束；仍由应用层用 `uuid4()` 生成，导入外部包时保留外部值。
- `entries` 新增 `review`、`lifecycle_state`，来自已冻结的标签评分契约；`EntryRead` 目前未暴露，
  由成员二决定是否加入接口。
- 事务约定差异：成员二已合并的条目/资源仓储在方法内部 `commit()`，本次新增的标签类仓储
  只 `flush()`。统一到「应用服务提交」属于后续重构，不阻塞当前合并。
- 另外发现 `app/db/resource_repository.py` 反向导入了 `app.application.ports.StoredResource`，
  与 `backend/README.md` 的 `api → application → db` 方向相反。建议后续把 `StoredResource`
  移到 `app/db/records.py` 或 `app.domain`，让数据层不依赖应用层。

### 成员三：标签与评分

- `tag_categories`、`tags`、`entry_tags` 已按契约建好：分类名 NOCASE 唯一、分类内
  `(category_id, normalized_name)` 唯一、评分可空 1 至 10、分类删除为 RESTRICT。
- 删除仍被引用的标签时数据库返回 RESTRICT，不级联删除关系；请在服务层先用
  `entry_tag_repository.count_by_tag(tag_id)` 判断并返回 409（契约第 9 条）。
- 系统分类「未分类标签」由迁移写入（`system_key = 'uncategorized'`），不需要应用层再建。
- 数据层仓储返回 dataclass，不依赖 `app.domain`。请在你的服务里映射成 `TagRead` 等模型，
  避免两边同时定义同一领域类造成冲突。
- `normalized_name` 由数据层用 `casefold()` 生成，标签重名判断请直接查
  `tag_repository.find(category_id, name)`，不要自己再算一遍。
- 契约已合并进 main（PR #22），`backend/app/db/README.md` 以 `docs/tag-rating-contract.md` 为准。

### 成员四：检索与展示

- 已建索引：`entries.title`、`resources.entry_id`、`resources.sha256`、
  `entry_tags.tag_id`、`tags.category_id`。
- 关键词搜索在 Alpha 阶段建议先用 `LIKE` 并记录 1000 条数据下的基线；确需 FTS5 时新增
  独立迁移，不要改 0001/0002。
- 分页请使用 `LIMIT/OFFSET` + 稳定排序（`created_at DESC, id DESC`），避免翻页重复。

### 成员五：分享包

- 分享包只用 `share_id`，不带 SQLite 自增 `id`。
- 在 0002 之后标签不再有 `share_id`，导出时用临时 `tag_ref`，与契约一致。

### 成员八：质量与发布

- CI 的 `compileall` 与 `pytest` 已能在本分支通过；迁移脚本会被一并编译。
- 打包时 Alembic 目录需要随包分发：在 PyInstaller 命令里追加
  `--add-data "backend/alembic.ini;backend" --add-data "backend/migrations;backend/migrations"`
  （或 `--collect-submodules alembic`）。缺失时 `init_db()` 会回退到 `create_all`，
  但那样不会应用后续迁移。
- 桌面端首次启动会创建 `data/library.db` 并自动迁移；升级前建议先调用
  `app.db.backup.create_backup()`。

### 成员六：界面与交互

- 数据层不向前端暴露本地绝对路径，资源路径只在后端解析。
- 时间统一按 UTC 存取，界面按本地时区显示。

## 4. 后续实现顺序

1. 评审 `0002` 的迁移实现；契约本身已在 PR #22 冻结，`upgrade head` 即为新结构。
2. 成员三基于 `tag_repository` / `entry_tag_repository` 实现 M3-02、M3-03。
3. 成员二补级联删除与 `share_id` 回归测试。
4. 成员八在打包脚本中加入迁移目录，并验证首次启动迁移。
5. Alpha 之后再考虑：FTS5、仓储事务规则统一、迁移失败自动回滚备份。

## 5. 验收标准

- 空库能通过 `alembic upgrade head` 建出全部表，且 `PRAGMA foreign_key_check` 为空。
- 从 0001 带数据升级到 0002 后，条目、标签、评分不丢失，标签归入「未分类标签」。
- 删除条目级联删除资源与条目标签，标签定义保留。
- 同一分类内标签重名被拒绝，跨分类同名允许。
- 评分 0、11 被拒绝，1、10 与空值通过。
- 备份文件可被 `verify_backup()` 判定为健康，且保留份数不超过 10。
- `pytest` 全绿（当前 81 项）。

```powershell
cd backend
alembic current
alembic upgrade head
cd ..
pytest -q
```
