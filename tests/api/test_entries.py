from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_entry_service, get_search_service
from app.application.entry_service import EntryService
from app.application.search_service import SearchService
from app.db.base import Base
from app.db.entry_query_repository import SqliteEntryQueryRepository
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.domain.entry import EntryCreate, EntryType
from app.main import app


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def make_client() -> tuple[TestClient, EntryService, Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    session = session_factory()
    repository = SqliteEntryRepository(session)
    resource_repository = SqliteResourceRepository(session)
    entry_service = EntryService(repository, resource_repository)
    search_service = SearchService(SqliteEntryQueryRepository(session))

    app.dependency_overrides[get_entry_service] = lambda: entry_service
    app.dependency_overrides[get_search_service] = lambda: search_service

    return TestClient(app), entry_service, session


def test_create_get_update_delete_entry() -> None:
    client, _, session = make_client()
    try:
        created = client.post(
            "/api/entries",
            json={
                "title": "示例游戏",
                "type": "game",
                "description": "测试条目",
                "review": "一周目通关评价",
            },
        )

        assert created.status_code == 201
        entry = created.json()
        assert entry["id"] == 1
        assert entry["share_id"]
        assert entry["title"] == "示例游戏"
        assert entry["review"] == "一周目通关评价"
        assert entry["lifecycle_state"] == "library"
        assert entry["has_cover"] is False
        assert "cover_path" not in entry
        assert entry["created_at"].endswith("Z")
        assert entry["updated_at"].endswith("Z")

        entry_id = entry["id"]

        fetched = client.get(f"/api/entries/{entry_id}")
        assert fetched.status_code == 200
        assert fetched.json()["title"] == "示例游戏"
        assert fetched.json()["review"] == "一周目通关评价"
        assert "cover_path" not in fetched.json()

        updated = client.patch(
            f"/api/entries/{entry_id}",
            json={"title": "修改后的标题", "review": None},
        )
        assert updated.status_code == 200
        assert updated.json()["title"] == "修改后的标题"
        assert updated.json()["review"] is None

        deleted = client.delete(f"/api/entries/{entry_id}")
        assert deleted.status_code == 204
        assert deleted.content == b""

        missing = client.get(f"/api/entries/{entry_id}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "ENTRY_NOT_FOUND"
    finally:
        session.close()


def test_entry_review_too_long_and_patch_boundary_errors() -> None:
    client, _, session = make_client()
    try:
        too_long = client.post(
            "/api/entries",
            json={
                "title": "超长评价测试",
                "type": "book",
                "review": "字" * 10_001,
            },
        )
        assert too_long.status_code == 422
        assert too_long.json()["code"] == "ENTRY_REVIEW_TOO_LONG"

        created = client.post(
            "/api/entries",
            json={"title": "边界测试", "type": "book"},
        )
        entry_id = created.json()["id"]

        empty_patch = client.patch(f"/api/entries/{entry_id}", json={})
        assert empty_patch.status_code == 422
        assert empty_patch.json()["code"] == "VALIDATION_ERROR"

        null_title = client.patch(f"/api/entries/{entry_id}", json={"title": None})
        assert null_title.status_code == 422
        assert null_title.json()["code"] == "VALIDATION_ERROR"

        null_type = client.patch(f"/api/entries/{entry_id}", json={"type": None})
        assert null_type.status_code == 422
        assert null_type.json()["code"] == "VALIDATION_ERROR"

        too_long_patch = client.patch(
            f"/api/entries/{entry_id}",
            json={"review": "评" * 10_001},
        )
        assert too_long_patch.status_code == 422
        assert too_long_patch.json()["code"] == "ENTRY_REVIEW_TOO_LONG"
    finally:
        session.close()


def test_entry_cover_path_validation_and_temporary_visibility(tmp_path: Path) -> None:
    client, entry_service, session = make_client()
    try:
        rel_cover = client.post(
            "/api/entries",
            json={"title": "相对封面", "type": "image", "cover_path": "rel.png"},
        )
        assert rel_cover.status_code == 422
        assert rel_cover.json()["code"] == "RESOURCE_PATH_NOT_ABSOLUTE"

        missing_cover = client.post(
            "/api/entries",
            json={
                "title": "缺失封面",
                "type": "image",
                "cover_path": str(tmp_path / "missing.png"),
            },
        )
        assert missing_cover.status_code == 409
        assert missing_cover.json()["code"] == "RESOURCE_FILE_MISSING"

        cover_file = tmp_path / "cover.png"
        cover_file.write_bytes(b"cover-bytes")
        with_cover = client.post(
            "/api/entries",
            json={
                "title": "正式条目",
                "type": "image",
                "cover_path": str(cover_file),
            },
        )
        assert with_cover.status_code == 201
        assert with_cover.json()["has_cover"] is True
        assert str(cover_file) not in with_cover.text

        # 临时条目不得出现在 GET /api/entries 列表中；转正后才进入列表。
        temp = entry_service.create_temporary_entry(
            EntryCreate(title="隐藏临时条目", type=EntryType.BOOK)
        )
        listed_before = client.get("/api/entries").json()
        assert [item["title"] for item in listed_before["items"]] == ["正式条目"]

        entry_service.promote_temporary_entry(temp.id)
        listed_after = client.get("/api/entries").json()
        assert {item["title"] for item in listed_after["items"]} == {
            "正式条目",
            "隐藏临时条目",
        }
    finally:
        session.close()
