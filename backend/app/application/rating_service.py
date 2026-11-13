from app.application.errors import (
    EntryNotFoundError,
    EntryTagNotFoundError,
    TagNotFoundError,
)
from app.application.ports import (
    EntryRepository,
    EntryTagRepository,
    TagRepository,
)
from app.domain.tag import EntryTagRead, EntryTagUpsert


class RatingService:
    def __init__(
        self,
        *,
        entry_repository: EntryRepository,
        tag_repository: TagRepository,
        entry_tag_repository: EntryTagRepository,
    ) -> None:
        self.entry_repository = entry_repository
        self.tag_repository = tag_repository
        self.entry_tag_repository = entry_tag_repository

    def list_entry_tags(self, entry_id: int) -> list[EntryTagRead]:
        self._require_entry(entry_id)
        items: list[EntryTagRead] = []

        for relation in self.entry_tag_repository.list_by_entry(entry_id):
            tag = self.tag_repository.get(relation.tag_id)
            if tag is None:
                raise TagNotFoundError(f"标签 {relation.tag_id} 不存在")
            items.append(
                EntryTagRead(
                    entry_id=relation.entry_id,
                    tag_id=relation.tag_id,
                    tag_name=tag.name,
                    category_id=tag.category_id,
                    rating=relation.rating,
                    created_at=relation.created_at,
                    updated_at=relation.updated_at,
                )
            )
        return items

    def upsert_entry_tag(
        self,
        entry_id: int,
        tag_id: int,
        payload: EntryTagUpsert,
    ) -> EntryTagRead:
        self._require_entry(entry_id)
        tag = self.tag_repository.get(tag_id)
        if tag is None:
            raise TagNotFoundError(f"标签 {tag_id} 不存在")

        relation = self.entry_tag_repository.upsert(
            entry_id=entry_id,
            tag_id=tag_id,
            rating=payload.rating,
        )
        return EntryTagRead(
            entry_id=relation.entry_id,
            tag_id=relation.tag_id,
            tag_name=tag.name,
            category_id=tag.category_id,
            rating=relation.rating,
            created_at=relation.created_at,
            updated_at=relation.updated_at,
        )

    def remove_entry_tag(self, entry_id: int, tag_id: int) -> None:
        self._require_entry(entry_id)
        if self.tag_repository.get(tag_id) is None:
            raise TagNotFoundError(f"标签 {tag_id} 不存在")
        if not self.entry_tag_repository.delete(entry_id, tag_id):
            raise EntryTagNotFoundError("条目标签关系不存在")

    def _require_entry(self, entry_id: int) -> None:
        if self.entry_repository.get(entry_id) is None:
            raise EntryNotFoundError(f"条目 {entry_id} 不存在")
