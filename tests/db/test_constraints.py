"""数据库约束测试：外键、级联、唯一性与取值范围。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    EntryModel,
    EntryTagModel,
    ResourceModel,
    TagCategoryModel,
    TagModel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_entry(session: Session, title: str = "示例条目") -> EntryModel:
    entry = EntryModel(
        share_id=str(uuid4()),
        title=title,
        type="game",
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(entry)
    session.commit()
    return entry


def make_category(session: Session, name: str = "分类") -> TagCategoryModel:
    category = TagCategoryModel(
        name=name,
        sort_order=0,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(category)
    session.commit()
    return category


def make_tag(session: Session, category_id: int, name: str = "标签") -> TagModel:
    tag = TagModel(
        category_id=category_id,
        name=name,
        normalized_name=name.strip().casefold(),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(tag)
    session.commit()
    return tag


def test_foreign_keys_are_enabled(session: Session) -> None:
    assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_deleting_entry_cascades_resources_and_entry_tags(session: Session) -> None:
    entry = make_entry(session)
    category = make_category(session)
    tag = make_tag(session, category.id)

    session.add(
        ResourceModel(
            share_id=str(uuid4()),
            entry_id=entry.id,
            path="D:\\Media\\example.mp4",
            file_name="example.mp4",
            extension=".mp4",
            size_bytes=10,
            mtime_ns=1,
            sha256="a" * 64,
            availability="present",
            created_at=_now(),
        )
    )
    session.add(
        EntryTagModel(
            entry_id=entry.id,
            tag_id=tag.id,
            rating=5,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    session.commit()

    session.delete(entry)
    session.commit()

    remaining = session.execute(
        text("SELECT (SELECT COUNT(*) FROM resources), (SELECT COUNT(*) FROM entry_tags)")
    ).one()
    assert tuple(remaining) == (0, 0)

    # 标签定义不随条目删除而消失。
    assert session.execute(text("SELECT COUNT(*) FROM tags")).scalar() == 1


def test_deleting_referenced_tag_is_blocked(session: Session) -> None:
    """契约要求：删除仍被引用的标签必须冲突，不级联删除关系。"""
    entry = make_entry(session)
    category = make_category(session)
    tag = make_tag(session, category.id)

    session.add(
        EntryTagModel(
            entry_id=entry.id,
            tag_id=tag.id,
            rating=3,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    session.commit()

    session.delete(tag)

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    assert session.execute(text("SELECT COUNT(*) FROM entry_tags")).scalar() == 1


def test_deleting_unreferenced_tag_is_allowed(session: Session) -> None:
    category = make_category(session)
    tag = make_tag(session, category.id)

    session.delete(tag)
    session.commit()

    assert session.execute(text("SELECT COUNT(*) FROM tags")).scalar() == 0


def test_deleting_category_with_tags_is_blocked(session: Session) -> None:
    category = make_category(session)
    make_tag(session, category.id)

    session.delete(category)

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_share_id_is_unique(session: Session) -> None:
    shared = str(uuid4())
    first = make_entry(session)
    session.execute(
        text("UPDATE entries SET share_id = :share_id WHERE id = :id"),
        {"share_id": shared, "id": first.id},
    )
    session.commit()

    session.add(
        EntryModel(
            share_id=shared,
            title="重复 share_id",
            type="book",
            created_at=_now(),
            updated_at=_now(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_tag_name_unique_within_category(session: Session) -> None:
    category = make_category(session)
    make_tag(session, category.id, "动作")

    session.add(
        TagModel(
            category_id=category.id,
            name=" 动作 ",
            normalized_name="动作",
            created_at=_now(),
            updated_at=_now(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_tag_name_allowed_across_categories(session: Session) -> None:
    first = make_category(session, "分类一")
    second = make_category(session, "分类二")

    make_tag(session, first.id, "动作")
    make_tag(session, second.id, "动作")

    assert session.execute(text("SELECT COUNT(*) FROM tags")).scalar() == 2


def test_category_name_is_case_insensitive_unique(session: Session) -> None:
    make_category(session, "Games")

    session.add(
        TagCategoryModel(
            name="games",
            sort_order=1,
            created_at=_now(),
            updated_at=_now(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("rating", [1, 10, None])
def test_rating_accepts_valid_values(session: Session, rating: int | None) -> None:
    entry = make_entry(session)
    category = make_category(session)
    tag = make_tag(session, category.id)

    session.add(
        EntryTagModel(
            entry_id=entry.id,
            tag_id=tag.id,
            rating=rating,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    session.commit()

    assert session.execute(text("SELECT rating FROM entry_tags")).scalar() == rating


@pytest.mark.parametrize("rating", [0, 11, -1])
def test_rating_rejects_out_of_range(session: Session, rating: int) -> None:
    entry = make_entry(session)
    category = make_category(session)
    tag = make_tag(session, category.id)

    session.add(
        EntryTagModel(
            entry_id=entry.id,
            tag_id=tag.id,
            rating=rating,
            created_at=_now(),
            updated_at=_now(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_invalid_entry_type_is_rejected(session: Session) -> None:
    session.add(
        EntryModel(
            share_id=str(uuid4()),
            title="非法类型",
            type="unknown",
            created_at=_now(),
            updated_at=_now(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_invalid_resource_availability_is_rejected(session: Session) -> None:
    entry = make_entry(session)

    session.add(
        ResourceModel(
            share_id=str(uuid4()),
            entry_id=entry.id,
            path="D:\\Media\\example.mp4",
            file_name="example.mp4",
            extension=".mp4",
            size_bytes=1,
            mtime_ns=1,
            sha256="b" * 64,
            availability="unknown",
            created_at=_now(),
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_invalid_tag_color_is_rejected(session: Session) -> None:
    category = TagCategoryModel(
        name="带颜色分类",
        color="red",
        sort_order=0,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(category)

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
