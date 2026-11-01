"""数据层返回的记录类型与名称规范化。

这些是纯数据结构，不含业务规则。应用服务负责把它们转换成领域模型，
因此数据层不依赖 `app.domain`，避免和成员三的标签领域模型互相阻塞。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
