from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


def _normalized_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("名称不能为空")
    return cleaned


class TagCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalized_name(value)


class TagCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return None if value is None else _normalized_name(value)


class TagCreate(BaseModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=32)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalized_name(value)


class TagUpdate(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, max_length=32)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return None if value is None else _normalized_name(value)


class EntryTagUpsert(BaseModel):
    rating: StrictInt | None = Field(default=None, ge=1, le=10)


class TagCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None
    sort_order: int
    system_key: str | None
    created_at: datetime
    updated_at: datetime


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    created_at: datetime
    updated_at: datetime


class EntryTagRead(BaseModel):
    entry_id: int
    tag_id: int
    tag_name: str
    category_id: int
    rating: int | None
    created_at: datetime
    updated_at: datetime
