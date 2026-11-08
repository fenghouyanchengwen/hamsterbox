"""数据层返回的记录类型与名称规范化。

这些是纯数据结构，不含业务规则。数据层只依赖 `app.domain` 中的只读模型，
不依赖 `app.application` 或 `app.api`，调用方向保持 `api → application → db`。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.entry import ResourceRead


def clean_tag_name(name: str) -> str:
    """去掉首尾空白，保留用户输入的原始大小写。"""
    return name.strip()


def normalize_tag_name(name: str) -> str:
    """生成标签名的比较键：去空白后 casefold。"""
    return clean_tag_name(name).casefold()


@dataclass(frozen=True, slots=True)
class TagCategoryRecord:
    id: int
    name: str
    color: str | None
    sort_order: int
    system_key: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TagRecord:
    id: int
    category_id: int
    name: str
    normalized_name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class EntryTagRecord:
    entry_id: int
    tag_id: int
    rating: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AppSettingRecord:
    key: str
    value: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredResource:
    """资源的内部记录，`path` 只在后端内部使用，不进入 HTTP 响应。"""

    path: str
    data: ResourceRead
