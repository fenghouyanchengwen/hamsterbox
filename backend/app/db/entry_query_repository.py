"""条目检索的 SQLite 实现。

条件、排序与分页都在这里组装，排序只接受白名单值。
"""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import EntryModel, EntryTagModel
from app.db.records import EntryQueryRow

SORTS = ("updated_desc", "title_asc", "rating_desc")
_ESCAPE = "\\"


def _escape_like(value: str) -> str:
    for char in (_ESCAPE, "%", "_"):
        value = value.replace(char, _ESCAPE + char)
    return value


class SqliteEntryQueryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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
        if sort not in SORTS:
            raise ValueError(f"不支持的排序字段: {sort}")

        statement = (
            select(EntryModel)
            .where(
                *self._conditions(
                    keyword=keyword,
                    types=types,
                    tag_ids=tag_ids,
                    match_all_tags=match_all_tags,
                    rating_min=rating_min,
                    rating_max=rating_max,
                )
            )
            .order_by(*self._order_by(sort))
            .limit(limit)
            .offset(offset)
        )

        entries = list(self.session.scalars(statement))
        return self._with_tags(entries)

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
        statement = select(func.count()).select_from(EntryModel).where(
            *self._conditions(
                keyword=keyword,
                types=types,
                tag_ids=tag_ids,
                match_all_tags=match_all_tags,
                rating_min=rating_min,
                rating_max=rating_max,
            )
        )
        return int(self.session.scalar(statement) or 0)

    def _conditions(
        self,
        *,
        keyword: str | None,
        types: tuple[str, ...],
        tag_ids: tuple[int, ...],
        match_all_tags: bool,
        rating_min: int | None,
        rating_max: int | None,
    ) -> list:
        conditions = [EntryModel.lifecycle_state == "library"]

        if keyword:
            pattern = f"%{_escape_like(keyword)}%"
            conditions.append(
                or_(
                    EntryModel.title.like(pattern, escape=_ESCAPE),
                    EntryModel.description.like(pattern, escape=_ESCAPE),
                )
            )

        if types:
            conditions.append(EntryModel.type.in_(types))

        if tag_ids:
            if match_all_tags:
                for tag_id in tag_ids:
                    conditions.append(self._tag_exists(tag_id))
            else:
                conditions.append(
                    select(EntryTagModel.entry_id)
                    .where(EntryTagModel.tag_id.in_(tag_ids))
                    .where(EntryTagModel.entry_id == EntryModel.id)
                    .exists()
                )

        if rating_min is not None or rating_max is not None:
            rating_filter = [EntryTagModel.rating.is_not(None)]
            if rating_min is not None:
                rating_filter.append(EntryTagModel.rating >= rating_min)
            if rating_max is not None:
                rating_filter.append(EntryTagModel.rating <= rating_max)
            conditions.append(
                select(EntryTagModel.entry_id)
                .where(EntryTagModel.entry_id == EntryModel.id)
                .where(*rating_filter)
                .exists()
            )

        return conditions

    @staticmethod
    def _tag_exists(tag_id: int):
        return (
            select(EntryTagModel.entry_id)
            .where(EntryTagModel.entry_id == EntryModel.id)
            .where(EntryTagModel.tag_id == tag_id)
            .exists()
        )

    @staticmethod
    def _order_by(sort: str) -> list:
        if sort == "title_asc":
            return [func.lower(EntryModel.title).asc(), EntryModel.id.asc()]

        if sort == "rating_desc":
            average = (
                select(func.avg(EntryTagModel.rating))
                .where(EntryTagModel.entry_id == EntryModel.id)
                .scalar_subquery()
            )
            return [
                average.is_(None),
                average.desc(),
                EntryModel.updated_at.desc(),
                EntryModel.id.desc(),
            ]

        return [EntryModel.updated_at.desc(), EntryModel.id.desc()]

    def _with_tags(self, entries: list[EntryModel]) -> list[EntryQueryRow]:
        if not entries:
            return []

        rows = self.session.execute(
            select(EntryTagModel.entry_id, EntryTagModel.tag_id)
            .where(EntryTagModel.entry_id.in_([entry.id for entry in entries]))
            .order_by(EntryTagModel.entry_id, EntryTagModel.tag_id)
        ).all()

        grouped: dict[int, list[int]] = {}
        for entry_id, tag_id in rows:
            grouped.setdefault(entry_id, []).append(tag_id)

        return [
            EntryQueryRow(
                id=entry.id,
                share_id=entry.share_id,
                title=entry.title,
                type=entry.type,
                description=entry.description,
                cover_path=entry.cover_path,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                tag_ids=tuple(grouped.get(entry.id, ())),
            )
            for entry in entries
        ]
