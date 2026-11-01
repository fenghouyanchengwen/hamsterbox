"""迁移测试：空库可完整执行、版本链、降级与结构断言。"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.session import build_engine


def _columns(engine: Engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _indexes(engine: Engine, table: str) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes(table)}


def test_upgrade_to_0001_matches_main_contract(
    alembic_config: Config,
    database_path: Path,
) -> None:
    command.upgrade(alembic_config, "0001_alpha1_initial_schema")
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")

    try:
        assert {
            "entries",
            "resources",
            "tags",
            "entry_tags",
            "app_settings",
            "alembic_version",
        } <= _tables(engine)

        # 0001 是 main 契约：标签带 share_id/color/rating_enabled。
        assert {"share_id", "color", "rating_enabled"} <= _columns(engine, "tags")
        assert "review" in _columns(engine, "entry_tags")
        assert "review" not in _columns(engine, "entries")

        assert "ix_entries_title" in _indexes(engine, "entries")
        assert {"ix_resources_entry_id", "ix_resources_sha256"} <= _indexes(
            engine, "resources"
        )
        assert "ix_entry_tags_tag_id" in _indexes(engine, "entry_tags")
    finally:
        engine.dispose()


def test_upgrade_head_applies_member3_contract(
    alembic_config: Config,
    database_path: Path,
) -> None:
    command.upgrade(alembic_config, "head")
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")

    try:
        assert "tag_categories" in _tables(engine)

        tags = _columns(engine, "tags")
        assert {"category_id", "normalized_name"} <= tags
        assert not {"share_id", "color", "rating_enabled"} & tags

        entries = _columns(engine, "entries")
        assert {"review", "lifecycle_state"} <= entries

        entry_tags = _columns(engine, "entry_tags")
        assert "rating" in entry_tags
        assert "review" not in entry_tags

        with engine.connect() as connection:
            uncategorized = connection.execute(
                text(
                    "SELECT name FROM tag_categories WHERE system_key = 'uncategorized'"
                )
            ).scalar_one()
            assert uncategorized == "未分类标签"

            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert version == "0002_tag_category_review"

            assert connection.execute(text("PRAGMA foreign_key_check")).fetchall() == []
    finally:
        engine.dispose()


def test_migration_chain_is_idempotent(
    alembic_config: Config,
    database_path: Path,
) -> None:
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")

    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT COUNT(*) FROM tag_categories")).scalar()
                == 1
            )
    finally:
        engine.dispose()


def test_downgrade_to_base_removes_all_tables(
    alembic_config: Config,
    database_path: Path,
) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")

    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        remaining = _tables(engine) - {"alembic_version"}
        assert remaining == set()
    finally:
        engine.dispose()


def test_upgrade_preserves_existing_rows(
    alembic_config: Config,
    database_path: Path,
) -> None:
    """0001 上的既有数据升级到 0002 后不能丢失。"""
    command.upgrade(alembic_config, "0001_alpha1_initial_schema")

    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO entries "
                    "(id, share_id, title, type, description, cover_path, created_at, updated_at) "
                    "VALUES (1, 'entry-share', '旧条目', 'game', '旧简介', NULL, "
                    "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO tags "
                    "(id, share_id, name, color, rating_enabled, created_at, updated_at) "
                    "VALUES (1, 'tag-share', 'RPG', '#AABBCC', 1, "
                    "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO entry_tags "
                    "(entry_id, tag_id, rating, review, created_at, updated_at) "
                    "VALUES (1, 1, 3, '关系评价', "
                    "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
                )
            )
    finally:
        engine.dispose()

    command.upgrade(alembic_config, "head")

    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.connect() as connection:
            tag = connection.execute(
                text(
                    "SELECT t.name, t.normalized_name, c.system_key "
                    "FROM tags AS t JOIN tag_categories AS c ON c.id = t.category_id"
                )
            ).one()
            assert tuple(tag) == ("RPG", "rpg", "uncategorized")

            entry = connection.execute(
                text("SELECT title, description, review, lifecycle_state FROM entries")
            ).one()
            assert tuple(entry) == ("旧条目", "旧简介", None, "library")

            relation = connection.execute(
                text("SELECT rating FROM entry_tags")
            ).one()
            assert tuple(relation) == (3,)
    finally:
        engine.dispose()


def test_downgrade_restores_0001_shape(
    alembic_config: Config,
    database_path: Path,
) -> None:
    """从 head 降回 0001，应恢复 main 契约的列。"""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "0001_alpha1_initial_schema")

    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        assert {"share_id", "color", "rating_enabled"} <= _columns(engine, "tags")
        assert "review" in _columns(engine, "entry_tags")
        assert "review" not in _columns(engine, "entries")
        assert "tag_categories" not in _tables(engine)
    finally:
        engine.dispose()
