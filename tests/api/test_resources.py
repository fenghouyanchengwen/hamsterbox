from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_entry_service, get_resource_service
from app.application.entry_service import EntryService
from app.application.resource_service import ResourceService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.main import app


def test_resource_http_flow(tmp_path) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    entry_repository = SqliteEntryRepository(session)
    resource_repository = SqliteResourceRepository(session)

    app.dependency_overrides[get_entry_service] = lambda: EntryService(
        entry_repository
    )
    app.dependency_overrides[get_resource_service] = lambda: ResourceService(
        entry_repository,
        resource_repository,
    )

    try:
        client = TestClient(app)
        created = client.post(
            "/api/entries",
            json={"title": "示例", "type": "game"},
        )
        assert created.status_code == 201
        entry_id = created.json()["id"]

        file_path = tmp_path / "example.txt"
        file_path.write_text("hello", encoding="utf-8")

        attached = client.post(
            f"/api/entries/{entry_id}/resources",
            json={"path": str(file_path)},
        )
        assert attached.status_code == 201
        resource = attached.json()
        assert resource["file_name"] == "example.txt"
        assert "path" not in resource

        listed = client.get(f"/api/entries/{entry_id}/resources")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1

        resource_id = resource["id"]
        file_path.unlink()
        rechecked = client.post(f"/api/resources/{resource_id}/recheck")
        assert rechecked.status_code == 200
        assert rechecked.json()["availability"] == "missing"

        detached = client.delete(
            f"/api/entries/{entry_id}/resources/{resource_id}"
        )
        assert detached.status_code == 204
    finally:
        app.dependency_overrides.clear()
        session.close()
