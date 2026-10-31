from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntryType(str, Enum):
    GAME = "game"
    BOOK = "book"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    MODEL = "model"
    OTHER = "other"


class EntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: EntryType
    description: str | None = Field(default=None, max_length=20_000)
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


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    share_id: str
    title: str
    type: EntryType
    description: str | None
    cover_path: str | None
    created_at: datetime
    updated_at: datetime


class EntryDetail(EntryRead):
    resources: list[ResourceRead] = Field(default_factory=list)