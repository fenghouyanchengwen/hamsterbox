"""数据层测试夹具：临时 SQLite + Alembic 迁移。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.session import build_engine

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


def make_alembic_config(database_path: Path) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "library.db"


@pytest.fixture
def alembic_config(database_path: Path) -> Config:
    return make_alembic_config(database_path)


@pytest.fixture
def migrated_db(database_path: Path, alembic_config: Config) -> Path:
    command.upgrade(alembic_config, "head")
    return database_path


@pytest.fixture
def engine(migrated_db: Path) -> Iterator[Engine]:
    test_engine = build_engine(f"sqlite:///{migrated_db.as_posix()}")
    try:
        yield test_engine
    finally:
        test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as test_session:
        yield test_session
