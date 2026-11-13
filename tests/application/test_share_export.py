import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.share_export import ShareExportError, export_share_package
from app.db.base import Base
from app.db.models import EntryModel, EntryTagModel, ResourceModel, TagCategoryModel, TagModel
from app.db.share_export_repository import ShareExportRepository


@pytest.fixture
def sample(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    now = datetime.now(timezone.utc)
    file = tmp_path / "资源.txt"
    file.write_bytes(b"private media bytes")
    category = TagCategoryModel(name="分类", color="#123456", sort_order=0, created_at=now, updated_at=now)
    session.add(category)
    session.flush()
    tag = TagModel(category_id=category.id, name="剧情", normalized_name="剧情", created_at=now, updated_at=now)
    first = EntryModel(share_id=str(uuid4()), title="作品一", type="game", description=None,
                       review="整体评价", lifecycle_state="library", cover_path="/private/cover.png",
                       created_at=now, updated_at=now)
    second = EntryModel(share_id=str(uuid4()), title="作品二", type="book", description="简介",
                        review=None, lifecycle_state="library", created_at=now, updated_at=now)
    session.add_all([tag, first, second])
    session.flush()
    resource = ResourceModel(share_id=str(uuid4()), entry_id=first.id, path=str(file), file_name=file.name,
                             extension=".txt", size_bytes=1, sha256="0" * 64,
                             availability="present", created_at=now)
    session.add_all([
        resource,
        EntryTagModel(entry_id=first.id, tag_id=tag.id, rating=10, created_at=now, updated_at=now),
        EntryTagModel(entry_id=second.id, tag_id=tag.id, rating=None, created_at=now, updated_at=now),
    ])
    session.commit()
    yield session, first, second, resource, file
    session.close()
    engine.dispose()


def unpack(data):
    with ZipFile(BytesIO(data)) as archive:
        assert archive.namelist() == ["manifest.json"]
        return json.loads(archive.read("manifest.json"))


def test_exports_two_entries_with_fresh_hash_and_without_private_data(sample):
    session, first, second, resource, file = sample
    library_id = str(uuid4())
    result = export_share_package(ShareExportRepository(session), [first.id, second.id], library_id)
    manifest = unpack(result)
    a, b = manifest["entries"]
    assert manifest["source_library_id"] == library_id
    assert a["source_review"] == "整体评价" and a["share_review"] is None
    assert a["entry_tags"][0]["rating"] == 10 and b["entry_tags"][0]["rating"] is None
    assert a["tags"][0]["tag_ref"] == b["tags"][0]["tag_ref"]
    assert a["resources"][0]["sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()
    assert a["resources"][0]["size_bytes"] == file.stat().st_size
    text = json.dumps(manifest, ensure_ascii=False)
    assert str(file) not in text and "/private/cover.png" not in text
    assert "#123456" not in text and "category_id" not in text
    assert b"private media bytes" not in result
    assert file.read_bytes() == b"private media bytes"
    assert session.get(ResourceModel, resource.id).sha256 == "0" * 64


def test_missing_resource_is_recorded_without_path(sample):
    session, first, _, _, file = sample
    file.unlink()
    entry = unpack(export_share_package(ShareExportRepository(session), [first.id], str(uuid4())))["entries"][0]
    assert entry["resources"][0]["availability_at_export"] == "missing"
    assert entry["resources"][0]["sha256"] is None
    assert entry["resources"][0]["size_bytes"] is None


@pytest.mark.parametrize("ids", [[], [0], [True], [999], [1, 1]])
def test_invalid_entry_selection_is_rejected(sample, ids):
    session, *_ = sample
    with pytest.raises(ShareExportError):
        export_share_package(ShareExportRepository(session), ids, str(uuid4()))


def test_invalid_source_library_id_is_rejected(sample):
    session, first, *_ = sample
    with pytest.raises(ShareExportError, match="UUID"):
        export_share_package(ShareExportRepository(session), [first.id], "invalid")


def test_temporary_entries_are_not_exported_by_this_prototype(sample):
    session, first, *_ = sample
    first.lifecycle_state = "temporary"
    session.commit()
    with pytest.raises(ShareExportError, match="正式条目"):
        export_share_package(ShareExportRepository(session), [first.id], str(uuid4()))


def test_invalid_resource_name_does_not_leak_path(sample):
    session, first, _, resource, _ = sample
    resource.file_name = "../secret.txt"
    session.commit()
    with pytest.raises(ShareExportError, match="文件名不安全"):
        export_share_package(ShareExportRepository(session), [first.id], str(uuid4()))


def test_non_regular_file_is_rejected(sample):
    session, first, _, resource, file = sample
    resource.path = str(file.parent)
    session.commit()
    with pytest.raises(ShareExportError, match="资源不是普通文件|无法读取资源文件"):
        export_share_package(ShareExportRepository(session), [first.id], str(uuid4()))


def test_invalid_app_version_fails_schema_validation(sample):
    session, first, *_ = sample
    with pytest.raises(ShareExportError, match="不符合格式规范"):
        export_share_package(ShareExportRepository(session), [first.id], str(uuid4()), "")


def test_each_export_generates_fresh_package_and_tag_refs(sample):
    session, first, *_ = sample
    repo, library_id = ShareExportRepository(session), str(uuid4())
    a = unpack(export_share_package(repo, [first.id], library_id))
    b = unpack(export_share_package(repo, [first.id], library_id))
    assert a["package_id"] != b["package_id"]
    assert a["entries"][0]["tags"][0]["tag_ref"] != b["entries"][0]["tags"][0]["tag_ref"]
    assert a["entries"][0]["share_id"] == b["entries"][0]["share_id"]
