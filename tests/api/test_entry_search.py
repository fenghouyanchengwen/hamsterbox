"""条目检索 HTTP 接口测试。"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_search_service
from app.application.search_service import SearchService
from app.db.base import Base
from app.db.entry_query_repository import SqliteEntryQueryRepository
from app.db.models import EntryModel, EntryTagModel, TagCategoryModel, TagModel
from app.main import app

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.clear()


def make_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine, expire_on_commit=False)()
    app.dependency_overrides[get_search_service] = lambda: SearchService(
        SqliteEntryQueryRepository(session)
    )
    return TestClient(app), session


def seed(session: Session) -> dict[str, int]:
    category = TagCategoryModel(name="类型", created_at=NOW, updated_at=NOW)
    session.add(category)
    session.flush()

    action = TagModel(
        category_id=category.id,
        name="动作",
        normalized_name="动作",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(action)
    session.flush()

    zelda = EntryModel(
        share_id="share-zelda",
        title="塞尔达传说",
        type="game",
        description="开放世界",
        lifecycle_state="library",
        created_at=NOW,
        updated_at=NOW,
    )
    hades = EntryModel(
        share_id="share-hades",
        title="Hades",
        type="game",
        description="动作 roguelike",
        lifecycle_state="library",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add_all([zelda, hades])
    session.flush()

    session.add(
        EntryTagModel(
            entry_id=zelda.id,
            tag_id=action.id,
            rating=9,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.commit()

    return {"zelda": zelda.id, "hades": hades.id, "action": action.id}


def test_empty_library_returns_page_structure() -> None:
    client, _ = make_client()

    response = client.get("/api/entries")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_search_filters_and_returns_tag_ids() -> None:
    client, session = make_client()
    ids = seed(session)

    response = client.get("/api/entries", params={"q": "塞尔", "tag_id": [ids["action"]]})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "塞尔达传说"
    assert body["items"][0]["tag_ids"] == [ids["action"]]


def test_sort_and_pagination_are_reflected_in_response() -> None:
    client, session = make_client()
    seed(session)

    response = client.get(
        "/api/entries",
        params={"sort": "title_asc", "page": 1, "page_size": 1},
    )

    body = response.json()
    assert body["total"] == 2
    assert body["page_size"] == 1
    assert len(body["items"]) == 1


def test_rating_range_inverted_returns_stable_error() -> None:
    client, _ = make_client()

    response = client.get("/api/entries", params={"rating_min": 9, "rating_max": 3})

    assert response.status_code == 422
    assert response.json()["code"] == "RATING_RANGE_INVALID"


def test_invalid_query_parameters_are_rejected() -> None:
    client, _ = make_client()

    assert client.get("/api/entries", params={"rating_min": 0}).status_code == 422
    assert client.get("/api/entries", params={"page_size": 500}).status_code == 422
    assert client.get("/api/entries", params={"sort": "random"}).status_code == 422
    assert client.get("/api/entries", params={"tag_mode": "xor"}).status_code == 422


def test_page_beyond_last_page_is_not_an_error() -> None:
    client, session = make_client()
    seed(session)

    response = client.get("/api/entries", params={"page": 99, "page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 2
    assert body["page"] == 99
