from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.db.records import (
    EntryQueryRow,
    EntryTagRecord,
    StoredResource,
    TagCategoryRecord,
    TagRecord,
)
from app.domain.entry import EntryRead, EntryType, ResourceRead


class ResourceOpener(Protocol):
    """应用服务使用的系统打开能力。"""

    def open(self, path: Path) -> None:
        ...


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


class ResourceRepository(Protocol):
    def create(
        self,
        *,
        share_id: str,
        entry_id: int,
        path: str,
        file_name: str,
        extension: str,
        size_bytes: int,
        mtime_ns: int,
        sha256: str,
        availability: str,
        created_at: datetime,
    ) -> StoredResource:
        ...

    def get(self, resource_id: int) -> StoredResource | None:
        ...

    def list_by_entry(self, entry_id: int) -> list[ResourceRead]:
        ...

    def find_by_entry_path(self, entry_id: int, path: str) -> ResourceRead | None:
        ...

    def update(
        self,
        resource_id: int,
        values: dict[str, object],
    ) -> StoredResource | None:
        ...

    def delete(self, entry_id: int, resource_id: int) -> bool:
        ...


class TagCategoryRepository(Protocol):
    def list_all(self) -> list[TagCategoryRecord]:
        ...

    def get(self, category_id: int) -> TagCategoryRecord | None:
        ...

    def find_by_name(self, name: str) -> TagCategoryRecord | None:
        ...

    def find_by_system_key(self, system_key: str) -> TagCategoryRecord | None:
        ...

    def create(
        self,
        *,
        name: str,
        color: str | None = None,
        sort_order: int = 0,
        system_key: str | None = None,
        now: datetime | None = None,
    ) -> TagCategoryRecord:
        ...

    def update(
        self,
        category_id: int,
        values: dict[str, object],
    ) -> TagCategoryRecord | None:
        ...

    def delete(self, category_id: int) -> bool:
        ...

    def count_tags(self, category_id: int) -> int:
        ...


class TagRepository(Protocol):
    def list_all(self) -> list[TagRecord]:
        ...

    def list_by_category(self, category_id: int) -> list[TagRecord]:
        ...

    def get(self, tag_id: int) -> TagRecord | None:
        ...

    def find(self, category_id: int, name: str) -> TagRecord | None:
        ...

    def create(
        self,
        *,
        category_id: int,
        name: str,
        now: datetime | None = None,
    ) -> TagRecord:
        ...

    def update(
        self,
        tag_id: int,
        values: dict[str, object],
    ) -> TagRecord | None:
        ...

    def delete(self, tag_id: int) -> bool:
        ...


class EntryTagRepository(Protocol):
    def list_by_entry(self, entry_id: int) -> list[EntryTagRecord]:
        ...

    def get(self, entry_id: int, tag_id: int) -> EntryTagRecord | None:
        ...

    def upsert(
        self,
        *,
        entry_id: int,
        tag_id: int,
        rating: int | None,
        now: datetime | None = None,
    ) -> EntryTagRecord:
        ...

    def delete(self, entry_id: int, tag_id: int) -> bool:
        ...

    def count_by_tag(self, tag_id: int) -> int:
        ...


class EntryQueryRepository(Protocol):
    def search(
        self,
        *,
        keyword: str | None,
        types: tuple[str, ...],
        tag_ids: tuple[int, ...],
        match_all_tags: bool,
        rating_min: int | None,
        rating_max: int | None,
        sort: str,
        limit: int,
        offset: int,
    ) -> list[EntryQueryRow]:
        ...

    def count(
        self,
        *,
        keyword: str | None,
        types: tuple[str, ...],
        tag_ids: tuple[int, ...],
        match_all_tags: bool,
        rating_min: int | None,
        rating_max: int | None,
    ) -> int:
        ...
