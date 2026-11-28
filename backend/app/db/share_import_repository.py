"""分享包匹配和事务写入所需的 SQLite 操作。"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EntryModel, EntryTagModel, ResourceModel
from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository


class ShareImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = SqliteTagCategoryRepository(session)
        self.tags = SqliteTagRepository(session)

    def has_entry(self, share_id: str) -> bool:
        return self.session.scalar(select(EntryModel.id).where(EntryModel.share_id == share_id)) is not None

    def has_resource(self, share_id: str) -> bool:
        return self.session.scalar(select(ResourceModel.id).where(ResourceModel.share_id == share_id)) is not None

    def resource_paths_for_hash(self, digest: str) -> tuple[str, ...]:
        statement = (
            select(ResourceModel.path)
            .join(EntryModel, EntryModel.id == ResourceModel.entry_id)
            .where(ResourceModel.sha256 == digest, EntryModel.lifecycle_state == "library")
            .distinct()
            .order_by(ResourceModel.path)
        )
        return tuple(self.session.scalars(statement))

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.session.rollback()
        with self.session.begin():
            # 获取写锁后重查冲突，串行化同一资料库的并发导入。
            self.session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            yield

    def create_entry(self, entry: dict, now: datetime) -> int:
        model = EntryModel(
            share_id=entry["share_id"],
            title=entry["title"].strip(),
            type=entry["type"],
            description=entry["description"],
            review=entry["share_review"] or entry["source_review"],
            lifecycle_state="library",
            created_at=now,
            updated_at=now,
        )
        self.session.add(model)
        self.session.flush()
        return model.id

    def create_resource(
        self, entry_id: int, share_id: str, *, path: str, file_name: str,
        extension: str, size: int, mtime_ns: int, digest: str, now: datetime,
    ) -> None:
        self.session.add(ResourceModel(
            entry_id=entry_id,
            share_id=share_id,
            path=path,
            file_name=file_name,
            extension=extension,
            size_bytes=size,
            mtime_ns=mtime_ns,
            sha256=digest,
            availability="present",
            created_at=now,
        ))

    def add_rating(
        self, entry_id: int, category_id: int, name: str, rating: int | None, now: datetime,
    ) -> None:
        tag = self.tags.find(category_id, name)
        if tag is None:
            tag = self.tags.create(
                category_id=category_id,
                name=name,
                now=now,
            )
        self.session.add(EntryTagModel(
            entry_id=entry_id, tag_id=tag.id, rating=rating, created_at=now, updated_at=now,
        ))
