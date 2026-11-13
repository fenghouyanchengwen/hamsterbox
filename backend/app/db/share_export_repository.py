"""供分享包导出使用的只读数据库快照。"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EntryModel, EntryTagModel, ResourceModel, TagModel


@dataclass(frozen=True)
class ExportResource:
    share_id: str
    path: str
    file_name: str
    extension: str


@dataclass(frozen=True)
class ExportTag:
    local_id: int
    name: str
    rating: int | None


@dataclass(frozen=True)
class ExportEntry:
    share_id: str
    title: str
    type: str
    description: str | None
    review: str | None
    created_at: datetime
    updated_at: datetime
    resources: tuple[ExportResource, ...]
    tags: tuple[ExportTag, ...]


class ShareExportRepository:
    """只读取正式条目；不改变数据库，也不导出本地分类。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entry_id: int) -> ExportEntry | None:
        entry = self.session.get(EntryModel, entry_id)
        if entry is None or entry.lifecycle_state != "library":
            return None
        resources = self.session.scalars(
            select(ResourceModel).where(ResourceModel.entry_id == entry_id).order_by(ResourceModel.id)
        ).all()
        rows = self.session.execute(
            select(TagModel, EntryTagModel.rating)
            .join(EntryTagModel, EntryTagModel.tag_id == TagModel.id)
            .where(EntryTagModel.entry_id == entry_id)
            .order_by(TagModel.id)
        ).all()
        return ExportEntry(
            share_id=entry.share_id, title=entry.title, type=entry.type,
            description=entry.description, review=entry.review,
            created_at=entry.created_at, updated_at=entry.updated_at,
            resources=tuple(ExportResource(r.share_id, r.path, r.file_name, r.extension) for r in resources),
            tags=tuple(ExportTag(tag.id, tag.name, rating) for tag, rating in rows),
        )
