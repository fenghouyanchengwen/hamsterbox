from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.application.entry_service import EntryService
from app.application.errors import (
    InvalidEntryLifecycleError,
    NotFoundError,
    ResourceFileMissingError,
    ResourceNotFileError,
    ResourcePathNotAbsoluteError,
)
from app.domain.entry import (
    EntryCreate,
    EntryRead,
    EntryType,
    EntryUpdate,
    LifecycleState,
)


class InMemoryEntryRepository:
    def __init__(self) -> None:
        self.items: dict[int, EntryRead] = {}
        self.cover_paths: dict[int, str | None] = {}
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
        review: str | None = None,
        lifecycle_state: LifecycleState = LifecycleState.LIBRARY,
    ) -> EntryRead:
        entry_id = self.next_id
        self.cover_paths[entry_id] = cover_path
        item = EntryRead(
            id=entry_id,
            share_id=share_id,
            title=title,
            type=entry_type,
            description=description,
            review=review,
            lifecycle_state=lifecycle_state,
            has_cover=bool(cover_path),
            created_at=created_at,
            updated_at=updated_at,
        )
        self.items[entry_id] = item
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
        if "cover_path" in values:
            cover_path = values.pop("cover_path")
            self.cover_paths[entry_id] = cover_path
            data["has_cover"] = bool(cover_path)
        data.update(values)
        updated = EntryRead.model_validate(data)
        self.items[entry_id] = updated
        return updated

    def delete(self, entry_id: int) -> bool:
        if entry_id not in self.items:
            return False

        del self.items[entry_id]
        self.cover_paths.pop(entry_id, None)
        return True


def test_create_entry() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    entry = service.create_entry(
        EntryCreate(title="示例游戏", type=EntryType.GAME, review="通关评价")
    )

    assert entry.id == 1
    assert entry.title == "示例游戏"
    assert entry.type == EntryType.GAME
    assert entry.review == "通关评价"
    assert entry.lifecycle_state == LifecycleState.LIBRARY
    assert entry.has_cover is False


def test_get_missing_entry_raises_not_found() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    with pytest.raises(NotFoundError):
        service.get_entry(999)


def test_update_entry_and_clear_review() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    entry = service.create_entry(
        EntryCreate(title="旧标题", type=EntryType.GAME, review="初版评价")
    )

    updated = service.update_entry(
        entry.id,
        EntryUpdate(title="新标题", review=None),
    )

    assert updated.title == "新标题"
    assert updated.review is None


def test_cover_path_validation_and_redaction(tmp_path: Path) -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    with pytest.raises(ResourcePathNotAbsoluteError):
        service.create_entry(
            EntryCreate(title="相对路径封面", type=EntryType.IMAGE, cover_path="cover.png")
        )

    with pytest.raises(ResourceFileMissingError):
        service.create_entry(
            EntryCreate(
                title="缺失封面",
                type=EntryType.IMAGE,
                cover_path=str(tmp_path / "missing.png"),
            )
        )

    folder = tmp_path / "dir"
    folder.mkdir()
    with pytest.raises(ResourceNotFileError):
        service.create_entry(
            EntryCreate(title="目录封面", type=EntryType.IMAGE, cover_path=str(folder))
        )

    cover = tmp_path / "poster.png"
    cover.write_bytes(b"png-bytes")
    created = service.create_entry(
        EntryCreate(title="合法封面", type=EntryType.IMAGE, cover_path=str(cover))
    )
    assert created.has_cover is True
    assert str(cover) not in created.model_dump_json()
    assert repository.cover_paths[created.id] == str(cover.resolve())


def test_temporary_entry_lifecycle_protects_library_entries() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    library_entry = service.create_entry(EntryCreate(title="正式作品", type=EntryType.BOOK))
    temp_entry = service.create_temporary_entry(
        EntryCreate(title="派生临时条目", type=EntryType.BOOK, review="原评价")
    )
    assert temp_entry.lifecycle_state == LifecycleState.TEMPORARY

    # 正式条目不能被当作临时条目误删，也不能重复执行转正。
    with pytest.raises(InvalidEntryLifecycleError):
        service.discard_temporary_entry(library_entry.id)
    with pytest.raises(InvalidEntryLifecycleError):
        service.promote_temporary_entry(library_entry.id)

    promoted = service.promote_temporary_entry(temp_entry.id, review="分享新评价")
    assert promoted.lifecycle_state == LifecycleState.LIBRARY
    assert promoted.review == "分享新评价"

    temp_to_discard = service.create_temporary_entry(
        EntryCreate(title="取消分享的临时条目", type=EntryType.BOOK)
    )
    service.discard_temporary_entry(temp_to_discard.id)
    with pytest.raises(NotFoundError):
        service.get_entry(temp_to_discard.id)
    assert service.get_entry(library_entry.id).title == "正式作品"


def test_remove_entry_only_removes_from_repository() -> None:
    repository = InMemoryEntryRepository()
    service = EntryService(repository)

    entry = service.create_entry(
        EntryCreate(title="待移出", type=EntryType.GAME)
    )

    service.remove_entry(entry.id)

    with pytest.raises(NotFoundError):
        service.get_entry(entry.id)
