"""SQLAlchemy 数据模型。

模型反映当前迁移链的 head（0002_tag_category_review）。表结构的历史版本由
`backend/migrations/versions/` 中的迁移脚本保存，不在此重复。
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COLOR_PATTERN = "#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]"
ENTRY_TYPES = ("game", "book", "video", "audio", "image", "model", "other")


class EntryModel(Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint(
            "type IN ('game','book','video','audio','image','model','other')",
            name="ck_entries_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="library",
        server_default=text("'library'"),
    )
    cover_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ResourceModel(Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "availability IN ('present','missing')",
            name="ck_resources_availability",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE", name="fk_resources_entry_id"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mtime_ns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    availability: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TagCategoryModel(Base):
    """本地标签分类。颜色与分类不参与分享。"""

    __tablename__ = "tag_categories"
    __table_args__ = (
        CheckConstraint(
            f"color IS NULL OR color GLOB '{COLOR_PATTERN}'",
            name="ck_tag_categories_color",
        ),
        UniqueConstraint("name", name="uq_tag_categories_name"),
        UniqueConstraint("system_key", name="uq_tag_categories_system_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(32, collation="NOCASE"),
        nullable=False,
    )
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    system_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TagModel(Base):
    """标签定义。同一分类内按 normalized_name 唯一，允许跨分类同名。"""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "normalized_name",
            name="uq_tags_category_normalized_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "tag_categories.id",
            ondelete="RESTRICT",
            name="fk_tags_category_id",
        ),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class EntryTagModel(Base):
    """条目标签关系，评分可选，取值 1 至 10。"""

    __tablename__ = "entry_tags"
    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1 AND 10)",
            name="ck_entry_tags_rating",
        ),
    )

    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE", name="fk_entry_tags_entry_id"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="RESTRICT", name="fk_entry_tags_tag_id"),
        primary_key=True,
        index=True,
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AppSettingModel(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
