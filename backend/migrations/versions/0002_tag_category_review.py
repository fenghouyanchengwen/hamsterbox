"""标签分类与条目整体评价（成员三契约）

在 0001 基线上：

- 新增 `tag_categories`，并写入系统分类「未分类标签」（system_key=uncategorized）；
- `entries` 增加 `review`、`lifecycle_state`；
- `tags` 改为 `(category_id, normalized_name)` 唯一，移除 `share_id`、`color`、
  `rating_enabled`，保留 `name` 原文；
- `entry_tags` 评分区间改为 1 至 10，移除关系上的 `review`。

SQLite 不支持直接删除列或修改约束，本迁移采用"建新表 → 复制数据 → 重命名"的方式，
由 migrations/env.py 在迁移期间关闭外键约束，迁移结束后恢复。

Revision ID: 0002_tag_category_review
Revises: 0001_alpha1_initial_schema
Create Date: 2026-11-01
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0002_tag_category_review"
down_revision = "0001_alpha1_initial_schema"
branch_labels = None
depends_on = None

COLOR_PATTERN = "#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
UNCATEGORIZED_KEY = "uncategorized"
UNCATEGORIZED_NAME = "未分类标签"

tags_new = sa.table(
    "tags_new",
    sa.column("id", sa.Integer),
    sa.column("category_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("normalized_name", sa.String),
    # SQLite 以 TEXT 存储时间；用 Text 声明可避免 DateTime 绑定处理器拒绝
    # 从数据库读出的字符串（真实数据升级时会遇到）。
    sa.column("created_at", sa.Text),
    sa.column("updated_at", sa.Text),
)


def _create_tag_categories() -> None:
    op.create_table(
        "tag_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=32, collation="NOCASE"), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("system_key", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            f"color IS NULL OR color GLOB '{COLOR_PATTERN}'",
            name="ck_tag_categories_color",
        ),
        sa.UniqueConstraint("name", name="uq_tag_categories_name"),
        sa.UniqueConstraint("system_key", name="uq_tag_categories_system_key"),
    )


def _ensure_uncategorized_category() -> int:
    """确保系统分类存在，返回其主键。"""
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    existing = bind.execute(
        sa.text("SELECT id FROM tag_categories WHERE system_key = :key"),
        {"key": UNCATEGORIZED_KEY},
    ).scalar()

    if existing is not None:
        return int(existing)

    bind.execute(
        sa.text(
            "INSERT INTO tag_categories "
            "(name, color, sort_order, system_key, created_at, updated_at) "
            "VALUES (:name, NULL, 0, :key, :created_at, :updated_at)"
        ),
        {
            "name": UNCATEGORIZED_NAME,
            "key": UNCATEGORIZED_KEY,
            "created_at": now,
            "updated_at": now,
        },
    )
    return int(
        bind.execute(
            sa.text("SELECT id FROM tag_categories WHERE system_key = :key"),
            {"key": UNCATEGORIZED_KEY},
        ).scalar_one()
    )


def _rebuild_tags(uncategorized_id: int) -> None:
    bind = op.get_bind()
    op.create_table(
        "tags_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("normalized_name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["tag_categories.id"],
            name="fk_tags_category_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "category_id",
            "normalized_name",
            name="uq_tags_category_normalized_name",
        ),
    )

    rows = bind.execute(
        sa.text("SELECT id, name, created_at, updated_at FROM tags ORDER BY id")
    ).fetchall()

    if rows:
        bind.execute(
            sa.insert(tags_new),
            [
                {
                    "id": row.id,
                    "category_id": uncategorized_id,
                    "name": row.name,
                    "normalized_name": row.name.strip().casefold(),
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ],
        )

    op.drop_table("tags")
    op.rename_table("tags_new", "tags")
    op.create_index("ix_tags_category_id", "tags", ["category_id"])


def _rebuild_entry_tags() -> None:
    bind = op.get_bind()
    op.create_table(
        "entry_tags_new",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1 AND 10)",
            name="ck_entry_tags_rating",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["entries.id"],
            name="fk_entry_tags_entry_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name="fk_entry_tags_tag_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("entry_id", "tag_id", name="pk_entry_tags"),
    )

    bind.execute(
        sa.text(
            "INSERT INTO entry_tags_new "
            "(entry_id, tag_id, rating, created_at, updated_at) "
            "SELECT entry_id, tag_id, rating, created_at, updated_at FROM entry_tags"
        )
    )

    op.drop_table("entry_tags")
    op.rename_table("entry_tags_new", "entry_tags")
    op.create_index("ix_entry_tags_tag_id", "entry_tags", ["tag_id"])


def upgrade() -> None:
    _create_tag_categories()
    uncategorized_id = _ensure_uncategorized_category()

    op.add_column("entries", sa.Column("review", sa.Text(), nullable=True))
    op.add_column(
        "entries",
        sa.Column(
            "lifecycle_state",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'library'"),
        ),
    )

    _rebuild_entry_tags()
    _rebuild_tags(uncategorized_id)


def downgrade() -> None:
    bind = op.get_bind()

    # 1. entry_tags 回到 0001：恢复 review 列与 1 至 5 分约束。
    op.create_table(
        "entry_tags_v1",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("review", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1 AND 5)",
            name="ck_entry_tags_rating",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["entries.id"],
            name="fk_entry_tags_entry_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name="fk_entry_tags_tag_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("entry_id", "tag_id", name="pk_entry_tags"),
    )
    # 降级时超出 1 至 5 的评分无法表达，置空以免违反旧约束。
    bind.execute(
        sa.text(
            "INSERT INTO entry_tags_v1 "
            "(entry_id, tag_id, rating, review, created_at, updated_at) "
            "SELECT entry_id, tag_id, "
            "CASE WHEN rating BETWEEN 1 AND 5 THEN rating ELSE NULL END, "
            "NULL, created_at, updated_at FROM entry_tags"
        )
    )
    op.drop_table("entry_tags")
    op.rename_table("entry_tags_v1", "entry_tags")
    op.create_index("ix_entry_tags_tag_id", "entry_tags", ["tag_id"])

    # 2. tags 回到 0001：恢复 share_id、color、rating_enabled 与 NOCASE 唯一名。
    op.create_table(
        "tags_v1",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("share_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=32, collation="NOCASE"), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column(
            "rating_enabled", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            f"color IS NULL OR color GLOB '{COLOR_PATTERN}'",
            name="ck_tags_color",
        ),
        sa.CheckConstraint(
            "rating_enabled IN (0,1)", name="ck_tags_rating_enabled"
        ),
        sa.UniqueConstraint("share_id", name="uq_tags_share_id"),
    )
    rows = bind.execute(
        sa.text("SELECT id, name, created_at, updated_at FROM tags ORDER BY id")
    ).fetchall()
    if rows:
        bind.execute(
            sa.text(
                "INSERT INTO tags_v1 "
                "(id, share_id, name, color, rating_enabled, created_at, updated_at) "
                "VALUES (:id, :share_id, :name, NULL, 0, :created_at, :updated_at)"
            ),
            [
                {
                    "id": row.id,
                    "share_id": str(uuid4()),
                    "name": row.name,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ],
        )
    op.drop_table("tags")
    op.rename_table("tags_v1", "tags")
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    # 3. entries 移除成员三新增列，然后删除分类表。
    with op.batch_alter_table("entries") as batch:
        batch.drop_column("lifecycle_state")
        batch.drop_column("review")

    op.drop_table("tag_categories")
