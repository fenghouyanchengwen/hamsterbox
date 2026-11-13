"""引擎配置与启动迁移测试。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

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
