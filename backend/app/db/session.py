"""SQLite 引擎、Session 与迁移入口。

数据库文件默认是 `data/library.db`，可用环境变量 `HAMSTERBOX_DB_PATH` 覆盖。
`init_db()` 通过 Alembic 升级到 head；只有在缺少迁移脚本（例如某些打包形态）时
才回退到 `Base.metadata.create_all`。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "library.db"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def database_path() -> Path:
    """解析数据库文件路径，必要时创建父目录。"""
    override = os.environ.get("HAMSTERBOX_DB_PATH")
    path = Path(override).expanduser() if override else DEFAULT_DATABASE_PATH
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def database_url() -> str:
    """解析数据库 URL，优先使用 `HAMSTERBOX_DB_URL`。"""
    override = os.environ.get("HAMSTERBOX_DB_URL")
    if override:
        return override
    return f"sqlite:///{database_path().as_posix()}"


def _apply_pragmas(dbapi_connection, connection_record) -> None:
    """每个连接建立后统一设置 SQLite 运行参数。"""
    cursor = dbapi_connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def build_engine(url: str | None = None) -> Engine:
    """创建引擎并挂载 SQLite PRAGMA 配置。"""
    engine = create_engine(
        url or database_url(),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    event.listen(engine, "connect", _apply_pragmas)
    return engine


DATABASE_PATH = database_path()
engine = build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_session() -> Session:
    return SessionLocal()


def init_db() -> None:
    """升级数据库到最新迁移版本。"""
    if _upgrade_to_head():
        return

    from app.db import models  # noqa: F401  注册模型后再建表

    Base.metadata.create_all(bind=engine)


def _upgrade_to_head() -> bool:
    if not ALEMBIC_INI.is_file():
        logger.warning("未找到 %s，回退到 create_all 建表", ALEMBIC_INI)
        return False

    from alembic import command
    from alembic.config import Config

    config = Config(str(ALEMBIC_INI))
    config.attributes["configure_logger"] = False
    # 传 URL 对象而不是字符串：set_main_option 会把值交给 configparser，
    # 而部分 SQLAlchemy 版本会把 "C:" 转义成 "C%3A"，"%": 触发插值错误。
    config.attributes["database_url"] = engine.url

    command.upgrade(config, "head")
    return True
