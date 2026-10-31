from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_entry_service
from app.application.entry_service import EntryService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.main import app


def make_client() -> TestClient:
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

    app.dependency_overrides[get_entry_service] = (
        lambda: EntryService(repository)
    )

    return TestClient(app)


def test_create_get_update_delete_entry() -> None:
    client = make_client()

    created = client.post(
        "/api/entries",
        json={
            "title": "示例游戏",
            "type": "game",
            "description": "测试条目",
        },
    )

    assert created.status_code == 201
    entry = created.json()
    assert entry["id"] == 1
    assert entry["share_id"]
    assert entry["title"] == "示例游戏"

    entry_id = entry["id"]

    fetched = client.get(f"/api/entries/{entry_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "示例游戏"

    updated = client.patch(
        f"/api/entries/{entry_id}",
        json={"title": "修改后的标题"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "修改后的标题"

    deleted = client.delete(f"/api/entries/{entry_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/api/entries/{entry_id}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "ENTRY_NOT_FOUND"