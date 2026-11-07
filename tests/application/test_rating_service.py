from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.errors import NotFoundError
from app.application.rating_service import RatingService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.db.entry_tag_repository import SqliteEntryTagRepository
from app.db.models import EntryModel, TagCategoryModel
from app.db.tag_repository import SqliteTagRepository
from app.domain.tag import EntryTagUpsert


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database_session:
        yield database_session
    engine.dispose()


@pytest.fixture
def service(session: Session) -> RatingService:
    return RatingService(
        entry_repository=SqliteEntryRepository(session),
        tag_repository=SqliteTagRepository(session),
        entry_tag_repository=SqliteEntryTagRepository(session),
    )


def create_entry_and_tag(session: Session) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    category = TagCategoryModel(
        name="分类",
        sort_order=0,
        created_at=now,
        updated_at=now,
    )
    session.add(category)
    session.flush()
    tag = SqliteTagRepository(session).create(
        category_id=category.id,
        name="动作",
    )
    entry = EntryModel(
        share_id="entry-1",
        title="示例条目",
        type="game",
        created_at=now,
        updated_at=now,
    )
    session.add(entry)
    session.flush()
    return entry.id, tag.id


def test_upsert_requires_existing_entry(session: Session, service: RatingService) -> None:
    _, tag_id = create_entry_and_tag(session)

    with pytest.raises(NotFoundError):
        service.upsert_entry_tag(999, tag_id, EntryTagUpsert(rating=8))


def test_upsert_requires_existing_tag(session: Session, service: RatingService) -> None:
    entry_id, _ = create_entry_and_tag(session)

    with pytest.raises(NotFoundError):
        service.upsert_entry_tag(entry_id, 999, EntryTagUpsert(rating=8))


def test_upsert_then_list_returns_tag_name_and_rating(
    session: Session,
    service: RatingService,
) -> None:
    entry_id, tag_id = create_entry_and_tag(session)

    service.upsert_entry_tag(entry_id, tag_id, EntryTagUpsert(rating=8))
    items = service.list_entry_tags(entry_id)

    assert len(items) == 1
    assert items[0].tag_id == tag_id
    assert items[0].tag_name == "动作"
    assert items[0].rating == 8


def test_upsert_is_idempotent_and_can_clear_rating(
    session: Session,
    service: RatingService,
) -> None:
    entry_id, tag_id = create_entry_and_tag(session)

    first = service.upsert_entry_tag(entry_id, tag_id, EntryTagUpsert(rating=6))
    second = service.upsert_entry_tag(entry_id, tag_id, EntryTagUpsert(rating=10))
    cleared = service.upsert_entry_tag(entry_id, tag_id, EntryTagUpsert(rating=None))

    assert first.rating == 6
    assert second.rating == 10
    assert cleared.rating is None
    assert len(service.list_entry_tags(entry_id)) == 1


def test_list_requires_existing_entry(service: RatingService) -> None:
    with pytest.raises(NotFoundError):
        service.list_entry_tags(999)


def test_remove_relation_keeps_tag_definition(
    session: Session,
    service: RatingService,
) -> None:
    entry_id, tag_id = create_entry_and_tag(session)
    service.upsert_entry_tag(entry_id, tag_id, EntryTagUpsert(rating=7))

    service.remove_entry_tag(entry_id, tag_id)

    assert service.list_entry_tags(entry_id) == []
    assert SqliteTagRepository(session).get(tag_id) is not None


def test_remove_missing_relation_is_not_found(
    session: Session,
    service: RatingService,
) -> None:
    entry_id, tag_id = create_entry_and_tag(session)

    with pytest.raises(NotFoundError):
        service.remove_entry_tag(entry_id, tag_id)
