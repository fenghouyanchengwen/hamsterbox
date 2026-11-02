"""Alpha 第一阶段初始表结构（main 契约基线）

覆盖 entries、resources、tags、entry_tags、app_settings，
字段与 backend/app/db/README.md 的 Alpha v0.1 定义一致。

Revision ID: 0001_alpha1_initial_schema
Revises:
Create Date: 2026-11-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_alpha1_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

ENTRY_TYPES = "'game','book','video','audio','image','model','other'"
COLOR_PATTERN = "#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"


def upgrade() -> None:
    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("share_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(f"type IN ({ENTRY_TYPES})", name="ck_entries_type"),
        sa.UniqueConstraint("share_id", name="uq_entries_share_id"),
    )
    op.create_index("ix_entries_title", "entries", ["title"])

    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("share_id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("mtime_ns", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("availability", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "availability IN ('present','missing')",
            name="ck_resources_availability",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["entries.id"],
            name="fk_resources_entry_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("share_id", name="uq_resources_share_id"),
    )
    op.create_index("ix_resources_entry_id", "resources", ["entry_id"])
    op.create_index("ix_resources_sha256", "resources", ["sha256"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("share_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=32, collation="NOCASE"), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column(
            "rating_enabled",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            f"color IS NULL OR color GLOB '{COLOR_PATTERN}'",
            name="ck_tags_color",
        ),
        sa.CheckConstraint(
            "rating_enabled IN (0,1)",
            name="ck_tags_rating_enabled",
        ),
        sa.UniqueConstraint("share_id", name="uq_tags_share_id"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "entry_tags",
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
    op.create_index("ix_entry_tags_tag_id", "entry_tags", ["tag_id"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_entry_tags_tag_id", table_name="entry_tags")
    op.drop_table("entry_tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_resources_sha256", table_name="resources")
    op.drop_index("ix_resources_entry_id", table_name="resources")
    op.drop_table("resources")
    op.drop_index("ix_entries_title", table_name="entries")
    op.drop_table("entries")
