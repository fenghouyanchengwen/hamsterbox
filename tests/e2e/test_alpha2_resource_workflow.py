"""End-to-end checks for resource integrity and library removal."""

from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_entry_service, get_resource_service
from app.application.entry_service import EntryService
from app.application.resource_service import ResourceService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Give each scenario an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session: Session = session_factory()
    entries = SqliteEntryRepository(session)
    resources = SqliteResourceRepository(session)

    app.dependency_overrides[get_entry_service] = lambda: EntryService(
        entries,
        resources,
    )
    app.dependency_overrides[get_resource_service] = lambda: ResourceService(
        entries,
        resources,
    )

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def create_entry(client: TestClient, title: str = "Alpha 二阶段资源校验") -> int:
    response = client.post(
        "/api/entries",
        json={"title": title, "type": "image"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_resource_hash_conflict_missing_recovery_and_detach(
    client: TestClient,
    tmp_path,
) -> None:
    """Exercise the current local-resource workflow through public APIs."""
    entry_id = create_entry(client)
    resource_path = tmp_path / "sample-image.webp"
    original_bytes = b"alpha2-resource-content-v1"
    resource_path.write_bytes(original_bytes)

    attached = client.post(
        f"/api/entries/{entry_id}/resources",
        json={"path": str(resource_path)},
    )

    assert attached.status_code == 201
    resource = attached.json()
    resource_id = resource["id"]
    assert resource["availability"] == "present"
    assert resource["sha256"] == sha256(original_bytes).hexdigest()
    assert "path" not in resource

    duplicate = client.post(
        f"/api/entries/{entry_id}/resources",
        json={"path": str(resource_path)},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "RESOURCE_ALREADY_LINKED"

    updated_bytes = b"alpha2-resource-content-v2-with-changes"
    resource_path.write_bytes(updated_bytes)
    changed = client.post(f"/api/resources/{resource_id}/recheck")
    assert changed.status_code == 200
    assert changed.json()["changed"] is True
    assert changed.json()["sha256"] == sha256(updated_bytes).hexdigest()

    resource_path.unlink()
    missing = client.post(f"/api/resources/{resource_id}/recheck")
    assert missing.status_code == 200
    assert missing.json()["availability"] == "missing"
    assert missing.json()["sha256"] is None

    resource_path.write_bytes(updated_bytes)
    recovered = client.post(f"/api/resources/{resource_id}/recheck")
    assert recovered.status_code == 200
    assert recovered.json()["availability"] == "present"
    assert recovered.json()["changed"] is True
    assert recovered.json()["sha256"] == sha256(updated_bytes).hexdigest()

    detached = client.delete(
        f"/api/entries/{entry_id}/resources/{resource_id}"
    )
    assert detached.status_code == 204
    assert resource_path.read_bytes() == updated_bytes

    listed = client.get(f"/api/entries/{entry_id}/resources")
    assert listed.status_code == 200
    assert listed.json() == {"items": [], "total": 0}


@pytest.mark.parametrize("remove_entry", [False, True], ids=["detach", "remove-entry"])
def test_removing_library_data_preserves_shared_file_and_other_entry(
    client: TestClient, tmp_path: Path, remove_entry: bool
) -> None:
    file_path = tmp_path / "共享图片.webp"
    contents = b"shared-resource"
    file_path.write_bytes(contents)

    first_entry = create_entry(client, "引用一")
    second_entry = create_entry(client, "引用二")
    payload = {"path": str(file_path)}
    first_link = client.post(f"/api/entries/{first_entry}/resources", json=payload)
    second_link = client.post(f"/api/entries/{second_entry}/resources", json=payload)
    assert first_link.status_code == second_link.status_code == 201
    first_resource_id = first_link.json()["id"]
    assert first_resource_id != second_link.json()["id"]

    if remove_entry:
        removed = client.delete(f"/api/entries/{first_entry}")
    else:
        removed = client.delete(f"/api/entries/{first_entry}/resources/{first_resource_id}")
    assert removed.status_code == 204

    first_resources = client.get(f"/api/entries/{first_entry}/resources")
    if remove_entry:
        assert first_resources.status_code == 404
    else:
        assert first_resources.status_code == 200
        assert first_resources.json() == {"items": [], "total": 0}

    second_resources = client.get(f"/api/entries/{second_entry}/resources")
    assert second_resources.status_code == 200
    assert second_resources.json() == {"items": [second_link.json()], "total": 1}
    assert file_path.read_bytes() == contents
