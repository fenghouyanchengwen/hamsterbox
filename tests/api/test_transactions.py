from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.api.dependencies as dependencies
from app.db.base import Base
from app.main import app


def test_entry_creation_commits_between_requests(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'library.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(dependencies, "get_session", factory)

    client = TestClient(app)
    created = client.post(
        "/api/entries",
        json={"title": "跨请求持久化", "type": "game"},
    )

    assert created.status_code == 201
    fetched = client.get(f"/api/entries/{created.json()['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "跨请求持久化"
