from collections.abc import Generator

from app.application.entry_service import EntryService
from app.db.entry_repository import SqliteEntryRepository
from app.db.session import get_session


def get_entry_service() -> Generator[EntryService, None, None]:
    session = get_session()

    try:
        repository = SqliteEntryRepository(session)
        yield EntryService(repository)
    finally:
        session.close()