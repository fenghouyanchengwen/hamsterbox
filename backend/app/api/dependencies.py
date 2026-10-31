from collections.abc import Generator

from app.application.entry_service import EntryService
from app.application.resource_service import ResourceService
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.db.session import get_session


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
