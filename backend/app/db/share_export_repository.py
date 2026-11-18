"""供分享包导出使用的只读数据库快照。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.db.models import AppSettingModel, EntryModel, EntryTagModel, ResourceModel, TagModel


@dataclass(frozen=True)
class ExportResource:
    share_id: str
    path: str
    file_name: str
    extension: str
    size_bytes: int | None = None
    sha256: str | None = None


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
    """读取正式条目的分享快照，维护本资料库的分享标识。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_library_id(self) -> str:
        key = "share.source_library_id"
        current = self.session.scalar(select(AppSettingModel.value).where(AppSettingModel.key == key))
        if current is not None:
            return current

        self.session.execute(
            insert(AppSettingModel).values(
                key=key, value=str(uuid4()), updated_at=datetime.now(timezone.utc)
            ).on_conflict_do_nothing(index_elements=[AppSettingModel.key])
        )
        library_id = self.session.execute(
            select(AppSettingModel.value).where(AppSettingModel.key == key)
        ).scalar_one()
        self.session.commit()
        return library_id

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
            resources=tuple(
                ExportResource(r.share_id, r.path, r.file_name, r.extension, r.size_bytes, r.sha256)
                for r in resources
            ),
            tags=tuple(ExportTag(tag.id, tag.name, rating) for tag, rating in rows),
        )
