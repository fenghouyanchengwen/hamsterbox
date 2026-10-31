from datetime import datetime
from typing import Protocol

from app.domain.entry import EntryRead, EntryType


class EntryRepository(Protocol):
    def create(
        self,
        *,
        share_id: str,
        title: str,
        entry_type: EntryType,
        description: str | None,
        cover_path: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> EntryRead:
        ...

    def get(self, entry_id: int) -> EntryRead | None:
        ...

    def update(
        self,
        entry_id: int,
        values: dict[str, object],
    ) -> EntryRead | None:
        ...

    def delete(self, entry_id: int) -> bool:
        ...