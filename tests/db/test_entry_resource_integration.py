"""迁移后的条目删除级联与原始文件保留（Issue #27 成员1/成员2 联调项）。

这些用例跑在 Alembic 迁移出来的真实表结构上，而不是 `create_all`，
因此同时验证迁移本身声明了正确的级联和唯一约束。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.entry_service import EntryService
from app.application.resource_service import ResourceService
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.domain.entry import EntryCreate, EntryType, ResourceCreate


def _services(session: Session) -> tuple[EntryService, ResourceService]:
    entry_repository = SqliteEntryRepository(session)
    resource_repository = SqliteResourceRepository(session)
    return (
        EntryService(entry_repository, resource_repository),
        ResourceService(entry_repository, resource_repository),
    )


def test_resources_table_declares_cascade_delete(session: Session) -> None:
    """resources.entry_id 必须是 ON DELETE CASCADE（迁移 0001 声明）。"""
    rows = session.execute(text("PRAGMA foreign_key_list(resources)")).fetchall()
    entry_foreign_keys = [row for row in rows if row[2] == "entries"]

    assert entry_foreign_keys, "resources 缺少指向 entries 的外键"
    # 列顺序：id, seq, table, from, to, on_update, on_delete, match
    assert entry_foreign_keys[0][6] == "CASCADE"


def test_entries_share_id_has_unique_index(session: Session) -> None:
    """entries.share_id 必须有唯一约束（分享包依赖它跨设备识别）。"""
    indexes = session.execute(text("PRAGMA index_list(entries)")).fetchall()
    unique_columns = []

    for index in indexes:
        if index[2] != 1:  # 2 = unique 标志位
            continue
        columns = session.execute(text(f"PRAGMA index_info('{index[1]}')")).fetchall()
        unique_columns.append([row[2] for row in columns])

    assert ["share_id"] in unique_columns


def test_share_id_duplicate_is_rejected(session: Session) -> None:
    repository = SqliteEntryRepository(session)
    now = datetime.now(timezone.utc)
    shared_id = "11111111-2222-3333-4444-555555555555"

    first = repository.create(
        share_id=shared_id,
        title="第一个条目",
        entry_type=EntryType.GAME,
        description=None,
        cover_path=None,
        created_at=now,
        updated_at=now,
    )
    assert first.share_id == shared_id

    with pytest.raises(IntegrityError):
        repository.create(
            share_id=shared_id,
            title="重复 share_id",
            entry_type=EntryType.BOOK,
            description=None,
            cover_path=None,
            created_at=now,
            updated_at=now,
        )

    session.rollback()
    assert session.execute(text("SELECT COUNT(*) FROM entries")).scalar() == 1


def test_remove_entry_deletes_resource_rows_but_keeps_file(
    session: Session,
    tmp_path: Path,
) -> None:
    entry_service, resource_service = _services(session)
    entry = entry_service.create_entry(
        EntryCreate(title="联调条目", type=EntryType.GAME)
    )

    payload = b"\x00\x01hamsterbox-original-file"
    media = tmp_path / "clip.mp4"
    media.write_bytes(payload)

    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(media)),
    )
    assert resource.availability == "present"
    assert session.execute(text("SELECT COUNT(*) FROM resources")).scalar() == 1

    entry_service.remove_entry(entry.id)

    # 数据库里的条目和资源记录都没了。
    assert session.execute(text("SELECT COUNT(*) FROM entries")).scalar() == 0
    assert session.execute(text("SELECT COUNT(*) FROM resources")).scalar() == 0

    # 磁盘上的原始文件必须原样保留。
    assert media.is_file()
    assert media.read_bytes() == payload


def test_detach_resource_keeps_file_on_disk(
    session: Session,
    tmp_path: Path,
) -> None:
    entry_service, resource_service = _services(session)
    entry = entry_service.create_entry(
        EntryCreate(title="解除关联条目", type=EntryType.VIDEO)
    )

    media = tmp_path / "detach.mp4"
    media.write_bytes(b"detach-payload")
    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(media)),
    )

    resource_service.detach_resource(entry.id, resource.id)

    assert session.execute(text("SELECT COUNT(*) FROM resources")).scalar() == 0
    assert media.is_file()
    assert media.read_bytes() == b"detach-payload"
