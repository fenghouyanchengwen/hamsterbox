from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.entry import EntryRead, EntryType, ResourceRead


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


@dataclass(frozen=True)
class StoredResource:
    """资源的内部记录，path 只在后端内部使用。"""

    path: str
    data: ResourceRead


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
