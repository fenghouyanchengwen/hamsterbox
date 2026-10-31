from datetime import datetime, timezone
from uuid import uuid4

from app.application.errors import NotFoundError
from app.application.ports import EntryRepository
from app.domain.entry import EntryCreate, EntryRead, EntryUpdate


class EntryService:
    def __init__(self, repository: EntryRepository) -> None:
        self.repository = repository

    def create_entry(self, payload: EntryCreate) -> EntryRead:
        now = datetime.now(timezone.utc)

        return self.repository.create(
            share_id=str(uuid4()),
            title=payload.title,
            entry_type=payload.type,
            description=payload.description,
            cover_path=payload.cover_path,
            created_at=now,
            updated_at=now,
        )

    def get_entry(self, entry_id: int) -> EntryRead:
        entry = self.repository.get(entry_id)

        if entry is None:
            raise NotFoundError(f"条目 {entry_id} 不存在")

        return entry

    def update_entry(
        self,
        entry_id: int,
        payload: EntryUpdate,
    ) -> EntryRead:
        self.get_entry(entry_id)

        values = payload.model_dump(exclude_unset=True)
        values["updated_at"] = datetime.now(timezone.utc)

        updated = self.repository.update(entry_id, values)

        if updated is None:
            raise NotFoundError(f"条目 {entry_id} 不存在")

        return updated

    def remove_entry(self, entry_id: int) -> None:
        self.get_entry(entry_id)

        deleted = self.repository.delete(entry_id)

        if not deleted:
            raise NotFoundError(f"条目 {entry_id} 不存在")