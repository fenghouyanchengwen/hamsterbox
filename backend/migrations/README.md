# 数据库迁移

| 项目 | 内容 |
|---|---|
| 用途 | 维护 Alembic 迁移脚本与升级/回滚流程 |
| 负责人 | 成员一：数据与存储 |
| 最后更新 | 2026-11-01 |

本目录由成员一负责初始化 Alembic 并维护迁移脚本。

## 目录

```
migrations/
  env.py                  # 数据库地址解析、SQLite PRAGMA、外键开关
  script.py.mako          # 新迁移模板
  versions/
    0001_alpha1_initial_schema.py   # 旧契约基线
    0002_tag_category_review.py     # 标签评分契约（PR #22 已冻结）
```

配置入口是 `backend/alembic.ini`。该文件必须是纯 ASCII：Windows 下 configparser
用系统默认编码（GBK）读取，中文注释会导致 `UnicodeDecodeError`。

## 常用命令

```powershell
cd backend
alembic current                          # 当前版本
alembic upgrade head                     # 升到最新
alembic upgrade 0001_alpha1_initial_schema   # 只升到 main 契约
alembic downgrade -1                     # 回退一步
alembic downgrade base                   # 清空数据库结构
alembic revision -m "add xxx"            # 新建空迁移
```

应用启动时 `app/db/session.py:init_db()` 会自动执行 `upgrade head`，
本地开发不需要手工升级。

## 版本链

```
0001_alpha1_initial_schema  ->  0002_tag_category_review
```

- `0001` 是旧契约基线（Alpha v0.1）。
- `0002` 对齐 PR #22 已冻结的标签评分契约，`upgrade head` 即为当前结构。
- 排查历史库时可只升到 `0001`，不需要删除迁移文件。

## 编写规则

- 迁移脚本必须可重复执行，并记录版本号。
- 修改表结构必须新建迁移，不直接改已有迁移；已合并的迁移视为不可变。
- 每个迁移必须能在空库上完整执行，并能 `downgrade` 回上一版本。
- SQLite 不支持直接删列或修改约束，使用"建新表 → 复制数据 → 重命名 → 重建索引"。
- 数据回填用 Python 计算（例如 `casefold()`），不要依赖 SQLite 的 `lower()` 近似。
- 不写死本机绝对路径；地址由 `env.py` 按 `config.attributes["database_url"]` →
  `sqlalchemy.url` → `HAMSTERBOX_DB_URL` → `data/library.db` 的顺序解析。
- 应用启动调用迁移时传的是 URL 对象而不是字符串：字符串会经过 configparser，
  Windows 盘符被转义成 `C%3A` 时 `%` 会触发插值错误。
- 迁移不得删除或改写用户原始媒体文件，只改数据库。

## 外键与安全

`env.py` 在迁移开始时关闭外键约束（SQLite 在事务内会忽略该 PRAGMA，因此必须在
SQLAlchemy 开启事务之前设置），迁移结束后执行 `PRAGMA foreign_key_check`：

- 检查通过才提交并恢复 `foreign_keys=ON`；
- 检查失败抛 `RuntimeError`，整次迁移回滚。

迁移连接同时设置 `journal_mode=WAL`、`synchronous=NORMAL`、`busy_timeout=5000`，
保证空库初始化完成后数据库文件直接是 WAL 模式。

## 升级前备份

`app/db/backup.py` 提供在线备份：

```python
from app.db.backup import create_backup, verify_backup

target = create_backup("data/library.db", "data/backups")
assert verify_backup(target)
```

规则见 `data/README.md`：备份前 checkpoint、文件名带时间戳、保留最近 10 份、
恢复后先做外键一致性检查。
