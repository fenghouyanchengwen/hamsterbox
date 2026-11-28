from datetime import datetime, timezone
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class EntryType(str, Enum):
    GAME = "game"
    BOOK = "book"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    MODEL = "model"
    OTHER = "other"


class LifecycleState(str, Enum):
    LIBRARY = "library"
    TEMPORARY = "temporary"


class EntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: EntryType
    description: str | None = Field(default=None, max_length=20_000)
    review: str | None = Field(default=None, max_length=10_000)
    cover_path: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value


class EntryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    type: EntryType | None = None
    description: str | None = Field(default=None, max_length=20_000)
    review: str | None = Field(default=None, max_length=10_000)
    cover_path: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value

    @model_validator(mode="after")
    def validate_non_empty_and_required_fields(self) -> "EntryUpdate":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一个修改字段")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("标题不能为空")
        if "type" in self.model_fields_set and self.type is None:
            raise ValueError("条目类型不能为空")
        return self


class ResourceCreate(BaseModel):
    path: str
    file_name: str | None = None


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    share_id: str
    entry_id: int
    file_name: str
    extension: str
    size_bytes: int | None
    mtime_ns: int | None
    sha256: str | None
    availability: str


class ResourceList(BaseModel):
    items: list[ResourceRead]
    total: int


class ResourceRecheck(ResourceRead):
    changed: bool


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    share_id: str
    title: str
    type: EntryType
    description: str | None
    review: str | None = None
    lifecycle_state: LifecycleState = LifecycleState.LIBRARY
    has_cover: bool = False
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def ensure_utc_timestamps(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class EntryDetail(EntryRead):
    resources: list[ResourceRead] = Field(default_factory=list)
