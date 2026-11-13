from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.errors import ConflictError, NotFoundError
from app.application.tag_service import TagService
from app.db.base import Base
from app.db.entry_tag_repository import SqliteEntryTagRepository
from app.db.models import EntryModel, TagCategoryModel
from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository
from app.domain.tag import TagCategoryCreate, TagCategoryUpdate, TagCreate, TagUpdate


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
        now = datetime.now(timezone.utc)
        database_session.add(
            TagCategoryModel(
                name="未分类标签",
                sort_order=0,
                system_key="uncategorized",
                created_at=now,
                updated_at=now,
            )
        )
        database_session.commit()
        yield database_session
    engine.dispose()


@pytest.fixture
def service(session: Session) -> TagService:
    return TagService(
        category_repository=SqliteTagCategoryRepository(session),
        tag_repository=SqliteTagRepository(session),
        entry_tag_repository=SqliteEntryTagRepository(session),
    )


def create_entry(session: Session) -> EntryModel:
    now = datetime.now(timezone.utc)
    entry = EntryModel(
        share_id="entry-1",
        title="示例条目",
        type="game",
        created_at=now,
        updated_at=now,
    )
    session.add(entry)
    session.flush()
    return entry


def test_create_category_rejects_duplicate_case_insensitive(
    service: TagService,
) -> None:
    service.create_category(TagCategoryCreate(name="Games"))

    with pytest.raises(ConflictError):
        service.create_category(TagCategoryCreate(name=" games "))


def test_update_category_rejects_duplicate_name(service: TagService) -> None:
    first = service.create_category(TagCategoryCreate(name="题材"))
    service.create_category(TagCategoryCreate(name="平台"))

    with pytest.raises(ConflictError):
        service.update_category(first.id, TagCategoryUpdate(name="平台"))


def test_create_tag_requires_existing_category(service: TagService) -> None:
    with pytest.raises(NotFoundError):
        service.create_tag(TagCreate(category_id=999, name="科幻"))


def test_update_tag_rejects_duplicate_in_target_category(
    service: TagService,
) -> None:
    first = service.create_category(TagCategoryCreate(name="分类一"))
    second = service.create_category(TagCategoryCreate(name="分类二"))
    service.create_tag(TagCreate(category_id=first.id, name="动作"))
    existing = service.create_tag(TagCreate(category_id=second.id, name="动作"))
    moving = service.create_tag(TagCreate(category_id=first.id, name="冒险"))

    with pytest.raises(ConflictError):
        service.update_tag(
            moving.id,
            TagUpdate(category_id=second.id, name=existing.name),
        )


def test_delete_referenced_tag_is_rejected(
    session: Session,
    service: TagService,
) -> None:
    category = service.create_category(TagCategoryCreate(name="分类"))
    tag = service.create_tag(TagCreate(category_id=category.id, name="动作"))
    entry = create_entry(session)
    SqliteEntryTagRepository(session).upsert(
        entry_id=entry.id,
        tag_id=tag.id,
        rating=8,
    )

    with pytest.raises(ConflictError):
        service.delete_tag(tag.id)


def test_delete_nonempty_category_is_rejected(service: TagService) -> None:
    category = service.create_category(TagCategoryCreate(name="分类"))
    service.create_tag(TagCreate(category_id=category.id, name="动作"))

    with pytest.raises(ConflictError):
        service.delete_category(category.id)


def test_delete_system_category_is_rejected(
    session: Session,
    service: TagService,
) -> None:
    system = SqliteTagCategoryRepository(session).find_by_system_key(
        "uncategorized"
    )
    assert system is not None

    with pytest.raises(ConflictError):
        service.delete_category(system.id)


def test_list_tags_filters_by_category(service: TagService) -> None:
    first = service.create_category(TagCategoryCreate(name="分类一"))
    second = service.create_category(TagCategoryCreate(name="分类二"))
    service.create_tag(TagCreate(category_id=first.id, name="动作"))
    service.create_tag(TagCreate(category_id=second.id, name="动作"))
    service.create_tag(TagCreate(category_id=second.id, name="冒险"))

    tags = service.list_tags(category_id=second.id)

    assert [tag.name for tag in tags] == ["冒险", "动作"]
