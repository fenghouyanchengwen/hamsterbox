from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import (
    get_entry_service,
    get_rating_service,
    get_tag_service,
)
from app.application.entry_service import EntryService
from app.application.rating_service import RatingService
from app.application.tag_service import TagService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.db.entry_tag_repository import SqliteEntryTagRepository
from app.db.models import TagCategoryModel
from app.db.resource_repository import SqliteResourceRepository
from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    now = datetime.now(timezone.utc)
    session.add(
        TagCategoryModel(
            name="未分类标签",
            sort_order=0,
            system_key="uncategorized",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()

    categories = SqliteTagCategoryRepository(session)
    tags = SqliteTagRepository(session)
    entry_tags = SqliteEntryTagRepository(session)
    tag_service = TagService(
        category_repository=categories,
        tag_repository=tags,
        entry_tag_repository=entry_tags,
    )
    rating_service = RatingService(
        entry_repository=SqliteEntryRepository(session),
        tag_repository=tags,
        entry_tag_repository=entry_tags,
    )
    app.dependency_overrides[get_tag_service] = lambda: tag_service
    app.dependency_overrides[get_rating_service] = lambda: rating_service
    app.dependency_overrides[get_entry_service] = lambda: EntryService(
        SqliteEntryRepository(session),
        SqliteResourceRepository(session),
    )

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_tag_category_crud(client: TestClient) -> None:
    created = client.post(
        "/api/tag-categories",
        json={"name": "  题材  ", "color": "#5B8FF9", "sort_order": 5},
    )

    assert created.status_code == 201
    assert created.json()["name"] == "题材"
    category_id = created.json()["id"]

    listed = client.get("/api/tag-categories")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()][-1] == "题材"

    updated = client.patch(
        f"/api/tag-categories/{category_id}",
        json={"name": "平台", "color": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "平台"
    assert updated.json()["color"] is None

    deleted = client.delete(f"/api/tag-categories/{category_id}")
    assert deleted.status_code == 204


def test_duplicate_category_name_returns_409(client: TestClient) -> None:
    client.post("/api/tag-categories", json={"name": "Games"})

    response = client.post("/api/tag-categories", json={"name": " games "})

    assert response.status_code == 409
    assert response.json()["code"] == "TAG_CATEGORY_NAME_DUPLICATED"


def test_invalid_category_color_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/tag-categories",
        json={"name": "题材", "color": "blue"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "TAG_CATEGORY_COLOR_INVALID"


def test_system_category_cannot_be_deleted(client: TestClient) -> None:
    categories = client.get("/api/tag-categories").json()
    system = next(item for item in categories if item["system_key"] == "uncategorized")

    response = client.delete(f"/api/tag-categories/{system['id']}")

    assert response.status_code == 409
    assert response.json()["code"] == "SYSTEM_CATEGORY_PROTECTED"


def create_category(client: TestClient, name: str) -> int:
    response = client.post("/api/tag-categories", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_tag_crud_and_category_filter(client: TestClient) -> None:
    first_category = create_category(client, "分类一")
    second_category = create_category(client, "分类二")

    created = client.post(
        "/api/tags",
        json={"category_id": first_category, "name": "  动作  "},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "动作"
    tag_id = created.json()["id"]

    same_name_other_category = client.post(
        "/api/tags",
        json={"category_id": second_category, "name": "动作"},
    )
    assert same_name_other_category.status_code == 201

    filtered = client.get(f"/api/tags?category_id={second_category}")
    assert filtered.status_code == 200
    assert [tag["name"] for tag in filtered.json()] == ["动作"]

    updated = client.patch(
        f"/api/tags/{tag_id}",
        json={"category_id": second_category, "name": "冒险"},
    )
    assert updated.status_code == 200
    assert updated.json()["category_id"] == second_category
    assert updated.json()["name"] == "冒险"

    deleted = client.delete(f"/api/tags/{tag_id}")
    assert deleted.status_code == 204


def test_duplicate_tag_in_category_returns_409(client: TestClient) -> None:
    category_id = create_category(client, "分类")
    client.post("/api/tags", json={"category_id": category_id, "name": "RPG"})

    response = client.post(
        "/api/tags",
        json={"category_id": category_id, "name": " rpg "},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "TAG_NAME_DUPLICATED"


def test_delete_nonempty_category_returns_409(client: TestClient) -> None:
    category_id = create_category(client, "分类")
    client.post("/api/tags", json={"category_id": category_id, "name": "动作"})

    response = client.delete(f"/api/tag-categories/{category_id}")

    assert response.status_code == 409
    assert response.json()["code"] == "TAG_CATEGORY_NOT_EMPTY"


def create_entry_and_tag(client: TestClient) -> tuple[int, int]:
    entry = client.post(
        "/api/entries",
        json={"title": "示例条目", "type": "game"},
    )
    assert entry.status_code == 201
    category_id = create_category(client, "分类")
    tag = client.post(
        "/api/tags",
        json={"category_id": category_id, "name": "动作"},
    )
    assert tag.status_code == 201
    return entry.json()["id"], tag.json()["id"]


def test_entry_tag_rating_flow(client: TestClient) -> None:
    entry_id, tag_id = create_entry_and_tag(client)

    created = client.put(
        f"/api/entries/{entry_id}/tags/{tag_id}",
        json={"rating": 9},
    )
    assert created.status_code == 200
    assert created.json()["rating"] == 9
    assert created.json()["tag_name"] == "动作"

    updated = client.put(
        f"/api/entries/{entry_id}/tags/{tag_id}",
        json={"rating": None},
    )
    assert updated.status_code == 200
    assert updated.json()["rating"] is None

    listed = client.get(f"/api/entries/{entry_id}/tags")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["tag_id"] == tag_id

    removed = client.delete(f"/api/entries/{entry_id}/tags/{tag_id}")
    assert removed.status_code == 204
    assert client.get(f"/api/entries/{entry_id}/tags").json() == []
    assert any(
        tag["id"] == tag_id
        for tag in client.get("/api/tags").json()
    )

    missing_relation = client.delete(
        f"/api/entries/{entry_id}/tags/{tag_id}"
    )
    assert missing_relation.status_code == 404
    assert missing_relation.json()["code"] == "ENTRY_TAG_NOT_FOUND"


@pytest.mark.parametrize("rating", [0, 11, 9.5, True])
def test_invalid_rating_returns_422(
    client: TestClient,
    rating: object,
) -> None:
    entry_id, tag_id = create_entry_and_tag(client)

    response = client.put(
        f"/api/entries/{entry_id}/tags/{tag_id}",
        json={"rating": rating},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "RATING_OUT_OF_RANGE"


def test_rating_missing_entry_returns_404(client: TestClient) -> None:
    _, tag_id = create_entry_and_tag(client)

    response = client.put(
        f"/api/entries/999/tags/{tag_id}",
        json={"rating": 8},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ENTRY_NOT_FOUND"


def test_rating_missing_tag_returns_404(client: TestClient) -> None:
    entry_id, _ = create_entry_and_tag(client)

    response = client.put(
        f"/api/entries/{entry_id}/tags/999",
        json={"rating": 8},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "TAG_NOT_FOUND"
