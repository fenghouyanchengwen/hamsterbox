"""条目检索的查询编排。"""

from app.application.errors import RatingRangeInvalidError
from app.application.ports import EntryQueryRepository
from app.domain.entry import EntryType
from app.domain.search import EntryListItem, EntryPage, EntryQuery


class SearchService:
    def __init__(self, repository: EntryQueryRepository) -> None:
        self.repository = repository

    def search_entries(self, query: EntryQuery) -> EntryPage:
        if (
            query.rating_min is not None
            and query.rating_max is not None
            and query.rating_min > query.rating_max
        ):
            raise RatingRangeInvalidError("评分区间下界不能大于上界")

        params = {
            "keyword": query.q,
            "types": tuple(entry_type.value for entry_type in query.types),
            "tag_ids": tuple(query.tag_ids),
            "match_all_tags": query.tag_mode.value == "and",
            "rating_min": query.rating_min,
            "rating_max": query.rating_max,
        }

        rows = self.repository.search(
            **params,
            sort=query.sort.value,
            limit=query.page_size,
            offset=(query.page - 1) * query.page_size,
        )
        total = self.repository.count(**params)

        return EntryPage(
            items=[
                EntryListItem(
                    id=row.id,
                    share_id=row.share_id,
                    title=row.title,
                    type=EntryType(row.type),
                    description=row.description,
                    cover_path=row.cover_path,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    tag_ids=list(row.tag_ids),
                )
                for row in rows
            ],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
