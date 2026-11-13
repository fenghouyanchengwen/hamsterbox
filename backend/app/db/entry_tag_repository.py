"""条目标签关系与评分的 SQLite 仓储。

每个 `(entry_id, tag_id)` 只有一条记录，评分可空，取值 1 至 10。
仓储不提交事务，由应用服务控制提交时机。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EntryTagModel
from app.db.records import EntryTagRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteEntryTagRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_entry(self, entry_id: int) -> list[EntryTagRecord]:
        statement = (
            select(EntryTagModel)
            .where(EntryTagModel.entry_id == entry_id)
            .order_by(EntryTagModel.tag_id)
        )
        return [self._to_record(model) for model in self.session.scalars(statement)]

    def list_by_tag(self, tag_id: int) -> list[EntryTagRecord]:
        statement = (
            select(EntryTagModel)
            .where(EntryTagModel.tag_id == tag_id)
            .order_by(EntryTagModel.entry_id)
        )
        return [self._to_record(model) for model in self.session.scalars(statement)]

    def get(self, entry_id: int, tag_id: int) -> EntryTagRecord | None:
        model = self.session.get(EntryTagModel, (entry_id, tag_id))
        return None if model is None else self._to_record(model)

    def upsert(
        self,
        *,
        entry_id: int,
        tag_id: int,
        rating: int | None,
        now: datetime | None = None,
    ) -> EntryTagRecord:
        """幂等写入关系与评分，重复调用只更新评分和更新时间。"""
        timestamp = now or _now()
        model = self.session.get(EntryTagModel, (entry_id, tag_id))

        if model is None:
            model = EntryTagModel(
                entry_id=entry_id,
                tag_id=tag_id,
                rating=rating,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self.session.add(model)
        else:
            model.rating = rating
            model.updated_at = timestamp

        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def delete(self, entry_id: int, tag_id: int) -> bool:
        model = self.session.get(EntryTagModel, (entry_id, tag_id))
        if model is None:
            return False

        self.session.delete(model)
        self.session.flush()
        return True

    def count_by_tag(self, tag_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(EntryTagModel)
            .where(EntryTagModel.tag_id == tag_id)
        )
        return int(self.session.scalar(statement) or 0)

    @staticmethod
    def _to_record(model: EntryTagModel) -> EntryTagRecord:
        return EntryTagRecord(
            entry_id=model.entry_id,
            tag_id=model.tag_id,
            rating=model.rating,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
