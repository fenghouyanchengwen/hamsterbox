from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.api import dependencies
from app.db.base import Base
from app.db.models import EntryModel, EntryTagModel, ResourceModel, TagCategoryModel
from app.db.session import build_engine
from app.main import app


IMPORT = "/api/share/import"
PREVIEW = f"{IMPORT}/preview"
BINARY = {"Content-Type": "application/octet-stream"}


@pytest.fixture
def libraries(tmp_path, monkeypatch):
    engines = [build_engine(f"sqlite:///{(tmp_path / name).as_posix()}") for name in ("sender.db", "receiver.db")]
    for engine in engines:
        Base.metadata.create_all(engine)
    factories = [sessionmaker(bind=engine, autoflush=False) for engine in engines]
    active = factories[:1]
    monkeypatch.setattr(dependencies, "get_session", lambda: active[0]())
    client = TestClient(app)
    try:
        yield client, active, factories
    finally:
        client.close()
        for engine in engines:
            engine.dispose()


def entry_with_file(client, title, path):
    created = client.post("/api/entries", json={"title": title, "type": "book"})
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]
    attached = client.post(f"/api/entries/{entry_id}/resources", json={"path": str(path)})
    assert attached.status_code == 201, attached.text
    return entry_id


def test_export_import_between_libraries_matches_verified_hash_and_is_idempotent(libraries, tmp_path):
    client, active, (sender, receiver) = libraries
    source = tmp_path / "source.txt"
    source.write_bytes(b"same content")
    source_id = entry_with_file(client, "分享的作品", source)
    source_missing = tmp_path / "deleted.txt"
    source_missing.write_bytes(b"never registered at the destination")
    assert client.post(f"/api/entries/{source_id}/resources", json={"path": str(source_missing)}).status_code == 201
    source_missing.unlink()

    group = client.post("/api/tag-categories", json={"name": "科目", "color": "#123456"})
    assert group.status_code == 201, group.text
    tag = client.post("/api/tags", json={"category_id": group.json()["id"], "name": "课堂"})
    assert tag.status_code == 201, tag.text
    tag_id = tag.json()["id"]
    rating = client.put(f"/api/entries/{source_id}/tags/{tag_id}", json={"rating": 9})
    assert rating.status_code < 300, rating.text
    with sender.begin() as session:
        session.get(EntryModel, source_id).review = "条目评价"

    export = client.post("/api/share/export", json={"entry_ids": [source_id]})
    assert export.status_code == 200, export.text
    package = export.content

    active[0] = receiver
    target = tmp_path / "renamed.txt"
    target.write_bytes(source.read_bytes())
    entry_with_file(client, "本地候选", target)

    preview = client.post(PREVIEW, content=package, headers=BINARY)
    assert preview.status_code == 200, preview.text
    assert str(target) not in preview.text and str(source) not in preview.text
    preview_data = preview.json()
    planned = preview_data["entries"][0]
    assert planned["status"] == "new"
    assert [item["status"] for item in planned["resources"]] == ["auto_linked", "missing"]
    with receiver() as session:
        assert len(session.scalars(select(EntryModel)).all()) == 1
        assert not session.scalars(select(TagCategoryModel)).all()

    params = {"preview_sha256": preview_data["package_sha256"]}
    changed = client.post(IMPORT, params=params, content=package + b"changed", headers=BINARY)
    assert changed.status_code == 409

    imported = client.post(IMPORT, params=params, content=package, headers=BINARY)
    assert imported.status_code == 200, imported.text
    item = imported.json()["imported"][0]
    assert item["entry_id"] != source_id
    assert item["share_id"] == planned["share_id"]
    with receiver() as session:
        entry = session.get(EntryModel, item["entry_id"])
        assert entry.title == "分享的作品" and entry.review == "条目评价"
        attached = session.scalars(select(ResourceModel).where(ResourceModel.entry_id == entry.id)).one()
        assert attached.path == str(target) and attached.file_name == target.name
        assert session.scalar(select(EntryTagModel.rating)) == 9
        assert session.scalar(select(TagCategoryModel.color)) is None
    assert target.read_bytes() == source.read_bytes()

    duplicate_preview = client.post(PREVIEW, content=package, headers=BINARY)
    assert duplicate_preview.json()["entries"][0]["status"] == "conflict"
    repeated = client.post(IMPORT, params=params, content=package, headers=BINARY)
    assert repeated.json()["imported"] == []
    assert repeated.json()["skipped_share_ids"] == [planned["share_id"]]


def test_ambiguous_and_stale_fingerprints_are_reported(libraries, tmp_path):
    client, active, (_, receiver) = libraries
    original = tmp_path / "source.txt"
    original.write_bytes(b"same content")
    entry_id = entry_with_file(client, "作品", original)
    data = client.post("/api/share/export", json={"entry_ids": [entry_id]}).content

    active[0] = receiver
    first, second = tmp_path / "candidate-a.txt", tmp_path / "candidate-b.txt"
    for candidate in [first, second]:
        candidate.write_bytes(original.read_bytes())
        entry_with_file(client, candidate.name, candidate)
    response = client.post(PREVIEW, content=data, headers=BINARY)
    assert response.status_code == 200, response.text
    status = response.json()["entries"][0]["resources"][0]
    assert (status["status"], status["candidate_count"]) == ("needs_selection", 2)

    first.write_bytes(b"changed")
    second.unlink()
    response = client.post(PREVIEW, content=data, headers=BINARY)
    assert response.json()["entries"][0]["resources"][0]["status"] == "missing"


def test_tag_conflict_rolls_back_batch_and_can_be_resolved_by_category(libraries):
    client, active, (_, receiver) = libraries
    active[0] = receiver
    example = Path(__file__).resolve().parents[2] / "docs/examples/share-package-v1/multi-entry.json"
    manifest = json.loads(example.read_text(encoding="utf-8"))
    second = manifest["entries"][1]
    existing = second["tags"][0]
    extra_ref = str(uuid4())
    second["tags"].append({"tag_ref": extra_ref, "name": existing["name"]})
    second["entry_tags"].append({"tag_ref": extra_ref, "rating": 10})
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        output.writestr("manifest.json", json.dumps(manifest))
    data = archive.getvalue()
    response = client.post(PREVIEW, content=data, headers=BINARY)
    assert response.status_code == 200, response.text
    assert response.json()["entries"][1]["tag_conflicts"] == [existing["name"]]
    params = {"preview_sha256": response.json()["package_sha256"]}
    result = client.post(IMPORT, params=params, content=data, headers=BINARY)
    assert result.status_code == 409
    with receiver() as session:
        assert not session.scalars(select(EntryModel)).all()
        assert not session.scalars(select(TagCategoryModel)).all()

    category = client.post("/api/tag-categories", json={"name": "额外分类"}).json()
    params["tag_category"] = f"{extra_ref}:{category['id']}"
    params["entry_share_id"] = second["share_id"]
    result = client.post(IMPORT, params=params, content=data, headers=BINARY)
    assert result.status_code == 200, result.text
    assert len(result.json()["imported"]) == 1
    with receiver() as session:
        assert session.scalars(select(EntryModel)).one().share_id == second["share_id"]
        assert set(session.scalars(select(EntryTagModel.rating))) == {None, 10}


def test_invalid_and_oversized_uploads_are_rejected(libraries, monkeypatch):
    client, *_ = libraries
    bad = client.post(PREVIEW, content=b"invalid", headers=BINARY)
    assert bad.status_code == 422
    assert bad.json()["code"] == "SHARE_PACKAGE_INVALID"

    monkeypatch.setattr("app.api.share.MAX_ARCHIVE_BYTES", 5)
    large = client.post(PREVIEW, content=b"too large", headers=BINARY)
    assert large.status_code == 422
    assert "大小限制" in large.json()["message"]
