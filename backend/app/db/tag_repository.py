"""标签定义的 SQLite 仓储。

同一分类内按 `normalized_name` 唯一，跨分类允许同名。仓储不提交事务，
由应用服务控制提交时机。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TagModel
from app.db.records import TagRecord, normalize_tag_name


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteTagRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[TagRecord]:
        statement = select(TagModel).order_by(TagModel.category_id, TagModel.name)
        return [self._to_record(model) for model in self.session.scalars(statement)]

    def list_by_category(self, category_id: int) -> list[TagRecord]:
        statement = (
            select(TagModel)
            .where(TagModel.category_id == category_id)
            .order_by(TagModel.name)
        )
        return [self._to_record(model) for model in self.session.scalars(statement)]

    def get(self, tag_id: int) -> TagRecord | None:
        model = self.session.get(TagModel, tag_id)
        return None if model is None else self._to_record(model)

    def find(self, category_id: int, name: str) -> TagRecord | None:
        """按分类和名称查找标签，大小写不敏感。"""
        statement = select(TagModel).where(
            TagModel.category_id == category_id,
            TagModel.normalized_name == normalize_tag_name(name),
        )
        model = self.session.scalar(statement)
        return None if model is None else self._to_record(model)

    def create(
        self,
        *,
        category_id: int,
        name: str,
        now: datetime | None = None,
    ) -> TagRecord:
        timestamp = now or _now()
        cleaned = name.strip()
        model = TagModel(
            category_id=category_id,
            name=cleaned,
            normalized_name=normalize_tag_name(cleaned),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def rename(
        self,
        tag_id: int,
        name: str,
        now: datetime | None = None,
    ) -> TagRecord | None:
        """修改标签名，同时刷新 `normalized_name`。"""
        model = self.session.get(TagModel, tag_id)
        if model is None:
            return None

        cleaned = name.strip()
        model.name = cleaned
        model.normalized_name = normalize_tag_name(cleaned)
        model.updated_at = now or _now()
        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def update(
        self,
        tag_id: int,
        values: dict[str, object],
    ) -> TagRecord | None:
        model = self.session.get(TagModel, tag_id)
        if model is None:
            return None

        for field, value in values.items():
            if field == "name" and isinstance(value, str):
                model.name = value.strip()
                model.normalized_name = normalize_tag_name(value)
            elif field == "category_id":
                model.category_id = int(value)

        model.updated_at = _now()
        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def delete(self, tag_id: int) -> bool:
        model = self.session.get(TagModel, tag_id)
        if model is None:
            return False

        self.session.delete(model)
        self.session.flush()
        return True

    @staticmethod
    def _to_record(model: TagModel) -> TagRecord:
        return TagRecord(
            id=model.id,
            category_id=model.category_id,
            name=model.name,
            normalized_name=model.normalized_name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
