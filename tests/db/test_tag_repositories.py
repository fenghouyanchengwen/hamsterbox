"""标签分类与标签仓储测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository


def test_category_create_list_and_order(session: Session) -> None:
    repository = SqliteTagCategoryRepository(session)

    repository.create(name="第二", sort_order=2)
    repository.create(name="第一", sort_order=1)
    session.commit()

    # 迁移会预置 sort_order=0 的「未分类标签」，新建的两项排在它之后。
    assert [item.name for item in repository.list_all()][-2:] == ["第一", "第二"]


def test_category_find_by_name_is_case_insensitive(session: Session) -> None:
    repository = SqliteTagCategoryRepository(session)
    created = repository.create(name="Games")
    session.commit()

    found = repository.find_by_name("games")

    assert found is not None
    assert found.id == created.id


def test_category_find_by_system_key(session: Session) -> None:
    repository = SqliteTagCategoryRepository(session)

    # 0002 迁移已写入系统分类，重复创建会违反唯一约束。
    found = repository.find_by_system_key("uncategorized")

    assert found is not None
    assert found.name == "未分类标签"


def test_category_update_and_count_tags(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    category = categories.create(name="旧名称", sort_order=0)
    tags.create(category_id=category.id, name="动作")
    session.commit()

    updated = categories.update(category.id, {"name": "新名称", "sort_order": 7})
    session.commit()

    assert updated is not None
    assert updated.name == "新名称"
    assert updated.sort_order == 7
    assert categories.count_tags(category.id) == 1


def test_category_delete(session: Session) -> None:
    repository = SqliteTagCategoryRepository(session)
    category = repository.create(name="待删除")
    session.commit()

    assert repository.delete(category.id) is True
    assert repository.delete(category.id) is False
    session.commit()

    assert repository.get(category.id) is None


def test_tag_name_is_trimmed_and_normalized(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    category = categories.create(name="分类")
    tag = tags.create(category_id=category.id, name="  RPG  ")
    session.commit()

    assert tag.name == "RPG"
    assert tag.normalized_name == "rpg"


def test_tag_find_ignores_case_and_spaces(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    category = categories.create(name="分类")
    created = tags.create(category_id=category.id, name="RPG")
    session.commit()

    found = tags.find(category.id, "  rpg ")

    assert found is not None
    assert found.id == created.id


def test_tag_rename_updates_normalized_name(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    category = categories.create(name="分类")
    created = tags.create(category_id=category.id, name="旧名")
    session.commit()

    renamed = tags.rename(created.id, "新名")
    session.commit()

    assert renamed is not None
    assert renamed.name == "新名"
    assert renamed.normalized_name == "新名"
    assert tags.find(category.id, "旧名") is None


def test_duplicate_tag_in_same_category_raises(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    category = categories.create(name="分类")
    tags.create(category_id=category.id, name="动作")

    # 仓储在 flush 时即失败，不等调用方 commit。
    with pytest.raises(IntegrityError):
        tags.create(category_id=category.id, name="  动作  ")

    session.rollback()


def test_same_tag_name_in_different_categories_is_allowed(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    first = categories.create(name="分类一")
    second = categories.create(name="分类二")

    tags.create(category_id=first.id, name="动作")
    tags.create(category_id=second.id, name="动作")
    session.commit()

    assert len(tags.list_by_category(first.id)) == 1
    assert len(tags.list_by_category(second.id)) == 1


def test_tag_delete(session: Session) -> None:
    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)

    category = categories.create(name="分类")
    tag = tags.create(category_id=category.id, name="动作")
    session.commit()

    assert tags.delete(tag.id) is True
    session.commit()

    assert tags.delete(tag.id) is False
    assert tags.list_all() == []
