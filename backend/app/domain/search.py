"""条目检索的查询条件与分页结果。"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.domain.entry import EntryRead, EntryType


class SortKey(str, Enum):
    UPDATED_DESC = "updated_desc"
    TITLE_ASC = "title_asc"
    RATING_DESC = "rating_desc"


class TagMode(str, Enum):
    AND = "and"
    OR = "or"


class EntryQuery(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    types: list[EntryType] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)
    tag_mode: TagMode = TagMode.AND
    rating_min: int | None = Field(default=None, ge=1, le=10)
    rating_max: int | None = Field(default=None, ge=1, le=10)
    sort: SortKey = SortKey.UPDATED_DESC
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

    @field_validator("q")
    @classmethod
    def strip_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class EntryListItem(EntryRead):
    tag_ids: list[int] = Field(default_factory=list)


class EntryPage(BaseModel):
    items: list[EntryListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
