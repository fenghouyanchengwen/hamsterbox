"""引擎配置与启动迁移测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from app.db.base import Base
from app.db import session as session_module


def test_build_engine_applies_sqlite_pragmas(tmp_path: Path) -> None:
    engine = session_module.build_engine(
        f"sqlite:///{(tmp_path / 'library.db').as_posix()}"
    )

    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
    finally:
        engine.dispose()


def test_database_path_honors_env_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "custom" / "my-library.db"
    monkeypatch.setenv("HAMSTERBOX_DB_PATH", str(target))

    assert session_module.database_path() == target.resolve()
    assert session_module.database_url() == f"sqlite:///{target.resolve().as_posix()}"


def test_database_url_honors_env_override(monkeypatch) -> None:
    monkeypatch.setenv("HAMSTERBOX_DB_URL", "sqlite:///:memory:")

    assert session_module.database_url() == "sqlite:///:memory:"


def test_init_db_runs_migrations(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "library.db"
    engine = session_module.build_engine(f"sqlite:///{target.as_posix()}")
    monkeypatch.setattr(session_module, "engine", engine)

    try:
        session_module.init_db()

        with engine.connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type = 'table'")
                )
            }
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert tables >= {"entries", "resources", "tags", "entry_tags", "app_settings"}
        assert version == "0002_tag_category_review"
    finally:
        engine.dispose()


def test_init_db_does_not_pass_url_through_configparser(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """回归：URL 曾以字符串塞进 configparser，Windows 盘符被转义成 C%3A 后崩溃。"""
    from alembic.config import Config

    target = tmp_path / "library.db"
    engine = session_module.build_engine(f"sqlite:///{target.as_posix()}")
    monkeypatch.setattr(session_module, "engine", engine)

    seen: dict[str, str] = {}
    original = Config.set_main_option

    def spy(self, name: str, value: str):  # type: ignore[no-untyped-def]
        seen[name] = value
        return original(self, name, value)

    monkeypatch.setattr(Config, "set_main_option", spy)

    try:
        session_module.init_db()
        assert target.is_file()
    finally:
        engine.dispose()

    assert "sqlalchemy.url" not in seen


def test_init_db_adopts_alpha_fallback_without_losing_rows(tmp_path: Path, monkeypatch) -> None:
    from app.db import models  # noqa: F401

    engine = session_module.build_engine(f"sqlite:///{(tmp_path / 'alpha.db').as_posix()}")
    monkeypatch.setattr(session_module, "engine", engine)
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO app_settings (key, value, updated_at) "
                "VALUES ('legacy', 'preserved', '2026-11-01 12:00:00')"
            ))
        session_module.init_db()
        session_module.init_db()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0002_tag_category_review"
            )
            assert connection.execute(text("SELECT value FROM app_settings WHERE key='legacy'")).scalar_one() == (
                "preserved"
            )
            assert connection.execute(text(
                "SELECT count(*) FROM tag_categories WHERE system_key='uncategorized'"
            )).scalar_one() == 1
    finally:
        engine.dispose()


def test_init_db_does_not_stamp_unrecognized_schema(tmp_path: Path, monkeypatch) -> None:
    engine = session_module.build_engine(f"sqlite:///{(tmp_path / 'unknown.db').as_posix()}")
    monkeypatch.setattr(session_module, "engine", engine)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE entries (id INTEGER PRIMARY KEY)")
        with pytest.raises(RuntimeError, match="未识别"):
            session_module.init_db()
        assert inspect(engine).get_table_names() == ["entries"]
    finally:
        engine.dispose()
