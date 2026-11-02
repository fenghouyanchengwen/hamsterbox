"""Alembic 运行环境。

数据库地址解析顺序：显式传入的 sqlalchemy.url → 环境变量 HAMSTERBOX_DB_URL →
默认的 data/library.db。SQLite 迁移期间关闭外键约束，迁移结束后再校验并开启。
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base  # noqa: E402
from app.db import models  # noqa: E402,F401  确保模型注册到 metadata

config = context.config
target_metadata = Base.metadata

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _database_url():
    """按约定顺序解析数据库地址。

    1. 应用启动时经 `config.attributes["database_url"]` 传入的 URL 对象；
    2. 命令行或测试显式设置的 `sqlalchemy.url`；
    3. 环境变量 HAMSTERBOX_DB_URL；
    4. 默认的 data/library.db。
    """
    from_attributes = config.attributes.get("database_url")
    if from_attributes is not None:
        return from_attributes

    explicit = config.get_main_option("sqlalchemy.url")
    if explicit:
        return explicit

    env_url = os.environ.get("HAMSTERBOX_DB_URL")
    if env_url:
        return env_url

    database_path = PROJECT_ROOT / "data" / "library.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{database_path.as_posix()}"


def _apply_sqlite_pragmas(connection) -> None:
    """迁移连接也使用 WAL 和相同的时间参数，保证空库初始化后即为 WAL。"""
    driver_connection = connection.connection.driver_connection
    if driver_connection is None:
        return

    try:
        driver_connection.execute("PRAGMA journal_mode=WAL")
        driver_connection.execute("PRAGMA synchronous=NORMAL")
        driver_connection.execute("PRAGMA busy_timeout=5000")
    except Exception:  # noqa: BLE001 - 非 SQLite 驱动时跳过
        pass


def _set_foreign_keys(connection, enabled: bool) -> None:
    """在 SQLite 原始连接上切换外键开关。

    必须在 SQLAlchemy 开启事务之前调用，SQLite 在事务内会忽略该 PRAGMA。
    """
    driver_connection = connection.connection.driver_connection
    if driver_connection is None:
        return

    try:
        driver_connection.execute(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}")
    except Exception:  # noqa: BLE001 - 非 SQLite 或有其他驱动时不影响迁移
        pass


def _configure(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        _database_url(),
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    with connectable.connect() as connection:
        _apply_sqlite_pragmas(connection)
        _set_foreign_keys(connection, enabled=False)
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()

        violations = connection.execute(text("PRAGMA foreign_key_check")).fetchall()
        if violations:
            raise RuntimeError(f"迁移后外键一致性检查失败：{violations[:5]}")

        _set_foreign_keys(connection, enabled=True)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
