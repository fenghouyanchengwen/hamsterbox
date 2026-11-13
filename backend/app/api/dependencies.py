from collections.abc import Generator

from app.application.entry_service import EntryService
from app.application.rating_service import RatingService
from app.application.resource_service import ResourceService
from app.application.search_service import SearchService
from app.application.tag_service import TagService
from app.db.entry_query_repository import SqliteEntryQueryRepository
from app.db.entry_repository import SqliteEntryRepository
from app.db.entry_tag_repository import SqliteEntryTagRepository
from app.db.resource_repository import SqliteResourceRepository
from app.db.session import get_session
from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository


def get_entry_service() -> Generator[EntryService, None, None]:
    session = get_session()

    try:
        yield EntryService(
            repository=SqliteEntryRepository(session),
            resource_repository=SqliteResourceRepository(session),
        )
    finally:
        session.close()


def get_resource_service() -> Generator[ResourceService, None, None]:
    """为每个请求创建资源服务和数据库会话。"""
    session = get_session()

    try:
        yield ResourceService(
            entry_repository=SqliteEntryRepository(session),
            resource_repository=SqliteResourceRepository(session),
        )
    finally:
        session.close()


def get_tag_service() -> Generator[TagService, None, None]:
    session = get_session()
    try:
        yield TagService(
            category_repository=SqliteTagCategoryRepository(session),
            tag_repository=SqliteTagRepository(session),
            entry_tag_repository=SqliteEntryTagRepository(session),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_search_service() -> Generator[SearchService, None, None]:
    session = get_session()
    try:
        yield SearchService(repository=SqliteEntryQueryRepository(session))
    finally:
        session.close()


def get_rating_service() -> Generator[RatingService, None, None]:
    session = get_session()
    try:
        yield RatingService(
            entry_repository=SqliteEntryRepository(session),
            tag_repository=SqliteTagRepository(session),
            entry_tag_repository=SqliteEntryTagRepository(session),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
