"""条目列表与检索接口。"""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_search_service
from app.application.search_service import SearchService
from app.domain.entry import EntryType
from app.domain.search import EntryPage, EntryQuery, SortKey, TagMode


router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=EntryPage)
def search_entries(
    q: str | None = Query(default=None, max_length=200, description="标题或简介关键词"),
    entry_type: list[EntryType] = Query(default_factory=list, alias="type"),
    tag_id: list[int] = Query(default_factory=list),
    tag_mode: TagMode = TagMode.AND,
    rating_min: int | None = Query(default=None, ge=1, le=10),
    rating_max: int | None = Query(default=None, ge=1, le=10),
    sort: SortKey = SortKey.UPDATED_DESC,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: SearchService = Depends(get_search_service),
) -> EntryPage:
    return service.search_entries(
        EntryQuery(
            q=q,
            types=entry_type,
            tag_ids=tag_id,
            tag_mode=tag_mode,
            rating_min=rating_min,
            rating_max=rating_max,
            sort=sort,
            page=page,
            page_size=page_size,
        )
    )
