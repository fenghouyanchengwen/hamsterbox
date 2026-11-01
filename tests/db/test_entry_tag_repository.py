"""条目标签关系与应用设置仓储测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.app_setting_repository import SqliteAppSettingRepository
from app.db.entry_tag_repository import SqliteEntryTagRepository
from app.db.models import EntryModel
from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_entry(session: Session) -> EntryModel:
    entry = EntryModel(
        share_id=str(uuid4()),
        title="示例条目",
        type="game",
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(entry)
    session.commit()
    return entry


def _make_tag(session: Session) -> int:
    category = SqliteTagCategoryRepository(session).create(name="分类")
    tag = SqliteTagRepository(session).create(category_id=category.id, name="动作")
    session.commit()
    return tag.id


def test_upsert_creates_then_updates_rating(session: Session) -> None:
    entry = _make_entry(session)
    tag_id = _make_tag(session)
    repository = SqliteEntryTagRepository(session)

    created = repository.upsert(entry_id=entry.id, tag_id=tag_id, rating=4)
    session.commit()

    first_time = created.updated_at
    later = _now() + timedelta(minutes=5)
    updated = repository.upsert(entry_id=entry.id, tag_id=tag_id, rating=9, now=later)
    session.commit()

    assert updated.rating == 9
    assert updated.created_at == created.created_at
    assert updated.updated_at > first_time


def test_upsert_allows_clearing_rating(session: Session) -> None:
    entry = _make_entry(session)
    tag_id = _make_tag(session)
    repository = SqliteEntryTagRepository(session)

    repository.upsert(entry_id=entry.id, tag_id=tag_id, rating=6)
    cleared = repository.upsert(entry_id=entry.id, tag_id=tag_id, rating=None)
    session.commit()

    assert cleared.rating is None


def test_list_and_count_by_tag(session: Session) -> None:
    entry = _make_entry(session)
    tag_id = _make_tag(session)
    repository = SqliteEntryTagRepository(session)

    repository.upsert(entry_id=entry.id, tag_id=tag_id, rating=10)
    session.commit()

    assert [record.tag_id for record in repository.list_by_entry(entry.id)] == [tag_id]
    assert [record.entry_id for record in repository.list_by_tag(tag_id)] == [entry.id]
    assert repository.count_by_tag(tag_id) == 1
    assert repository.get(entry.id, tag_id) is not None


def test_delete_relation_keeps_tag_definition(session: Session) -> None:
    entry = _make_entry(session)
    tag_id = _make_tag(session)
    repository = SqliteEntryTagRepository(session)

    repository.upsert(entry_id=entry.id, tag_id=tag_id, rating=5)
    session.commit()

    assert repository.delete(entry.id, tag_id) is True
    session.commit()

    assert repository.get(entry.id, tag_id) is None
    assert SqliteTagRepository(session).get(tag_id) is not None
    assert repository.delete(entry.id, tag_id) is False


def test_app_setting_roundtrip(session: Session) -> None:
    repository = SqliteAppSettingRepository(session)

    repository.set("theme", "dark")
    session.commit()

    assert repository.get_value("theme") == "dark"
    assert repository.get_value("missing") is None
    assert repository.get_value("missing", "fallback") == "fallback"

    updated = repository.set("theme", "light")
    session.commit()

    assert updated.value == "light"
    assert [record.key for record in repository.list_all()] == ["theme"]

    assert repository.delete("theme") is True
    session.commit()
    assert repository.get("theme") is None
    assert repository.delete("theme") is False
