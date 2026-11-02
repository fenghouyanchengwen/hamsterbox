from datetime import datetime
from typing import Any

import pytest

from app.application.entry_service import EntryService
from app.application.errors import NotFoundError
from app.domain.entry import EntryCreate, EntryRead, EntryType, EntryUpdate


class InMemoryEntryRepository:
    def __init__(self) -> None:
        self.items: dict[int, EntryRead] = {}
        self.next_id = 1

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
        item = EntryRead(
            id=self.next_id,
            share_id=share_id,
            title=title,
            type=entry_type,
            description=description,
            cover_path=cover_path,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.items[self.next_id] = item
        self.next_id += 1
        return item

    def get(self, entry_id: int) -> EntryRead | None:
        return self.items.get(entry_id)

    def update(
        self,
        entry_id: int,
        values: dict[str, Any],
    ) -> EntryRead | None:
        current = self.items.get(entry_id)

        if current is None:
            return None

        data = current.model_dump()
        data.update(values)
        updated = EntryRead.model_validate(data)
        self.items[entry_id] = updated
        return updated

    def delete(self, entry_id: int) -> bool:
        if entry_id not in self.items:
            return False

        del self.items[entry_id]
        return True



def test_create_entry() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    entry = service.create_entry(
        EntryCreate(title="示例游戏", type=EntryType.GAME)
    )

    assert entry.id == 1
    assert entry.title == "示例游戏"
    assert entry.type == EntryType.GAME


def test_get_missing_entry_raises_not_found() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    with pytest.raises(NotFoundError):
        service.get_entry(999)


def test_update_entry() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    entry = service.create_entry(
        EntryCreate(title="旧标题", type=EntryType.GAME)
    )

    updated = service.update_entry(
        entry.id,
        EntryUpdate(title="新标题"),
    )

    assert updated.title == "新标题"


def test_remove_entry_only_removes_from_repository() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    entry = service.create_entry(
        EntryCreate(title="待移出", type=EntryType.GAME)
    )

    service.remove_entry(entry.id)

    with pytest.raises(NotFoundError):
        service.get_entry(entry.id)
