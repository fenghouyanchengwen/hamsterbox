"""标签分类的 SQLite 仓储。

仓储只做数据访问：不提交事务，由应用服务决定事务边界（参见
`backend/app/application/README.md` 的事务规则）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import TagCategoryModel, TagModel
from app.db.records import TagCategoryRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteTagCategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[TagCategoryRecord]:
        statement = select(TagCategoryModel).order_by(
            TagCategoryModel.sort_order,
            TagCategoryModel.id,
        )
        return [self._to_record(model) for model in self.session.scalars(statement)]

    def get(self, category_id: int) -> TagCategoryRecord | None:
        model = self.session.get(TagCategoryModel, category_id)
        return None if model is None else self._to_record(model)

    def find_by_name(self, name: str) -> TagCategoryRecord | None:
        """按名称查找分类。唯一性由库内 NOCASE 唯一约束保证。"""
        normalized = name.strip()
        statement = select(TagCategoryModel).where(
            func.lower(TagCategoryModel.name) == normalized.lower()
        )
        model = self.session.scalar(statement)
        return None if model is None else self._to_record(model)

    def find_by_system_key(self, system_key: str) -> TagCategoryRecord | None:
        statement = select(TagCategoryModel).where(
            TagCategoryModel.system_key == system_key
        )
        model = self.session.scalar(statement)
        return None if model is None else self._to_record(model)

    def create(
        self,
        *,
        name: str,
        color: str | None = None,
        sort_order: int = 0,
        system_key: str | None = None,
        now: datetime | None = None,
    ) -> TagCategoryRecord:
        timestamp = now or _now()
        model = TagCategoryModel(
            name=name.strip(),
            color=color,
            sort_order=sort_order,
            system_key=system_key,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def update(
        self,
        category_id: int,
        values: dict[str, object],
    ) -> TagCategoryRecord | None:
        model = self.session.get(TagCategoryModel, category_id)
        if model is None:
            return None

        for field, value in values.items():
            if field == "name" and isinstance(value, str):
                value = value.strip()
            setattr(model, field, value)

        model.updated_at = _now()
        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def delete(self, category_id: int) -> bool:
        model = self.session.get(TagCategoryModel, category_id)
        if model is None:
            return False

        self.session.delete(model)
        self.session.flush()
        return True

    def count_tags(self, category_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(TagModel)
            .where(TagModel.category_id == category_id)
        )
        return int(self.session.scalar(statement) or 0)

    @staticmethod
    def _to_record(model: TagCategoryModel) -> TagCategoryRecord:
        return TagCategoryRecord(
            id=model.id,
            name=model.name,
            color=model.color,
            sort_order=model.sort_order,
            system_key=model.system_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
