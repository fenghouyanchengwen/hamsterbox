import pytest
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


def test_resource_delete_preview_and_recycle_bin_http_flow(tmp_path) -> None:
    from app.api.dependencies import get_type_detector

    recycled_paths = []

    class FakeRecycleBin:
        def move(self, path) -> None:
            recycled_paths.append(path)
            path.unlink()

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
        entry_repository,
        resource_repository,
    )
    app.dependency_overrides[get_resource_service] = lambda: ResourceService(
        entry_repository,
        resource_repository,
        type_detector=get_type_detector(),
        recycle_bin=FakeRecycleBin(),
    )

    try:
        client = TestClient(app)

        # 验证关联资源时对 other 条目的自动类型识别（Issue #32）。
        other_entry = client.post(
            "/api/entries",
            json={"title": "未分类电子书", "type": "other"},
        ).json()
        pdf_file = tmp_path / "guide.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 sample")
        pdf_res = client.post(
            f"/api/entries/{other_entry['id']}/resources",
            json={"path": str(pdf_file)},
        )
        assert pdf_res.status_code == 201
        assert client.get(f"/api/entries/{other_entry['id']}").json()["type"] == "book"

        # 验证跨条目共享引用预览与二次确认回收站删除（B1-A01 / B1-A02）。
        second_entry = client.post(
            "/api/entries",
            json={"title": "参考资料集", "type": "book"},
        ).json()
        shared_res = client.post(
            f"/api/entries/{second_entry['id']}/resources",
            json={"path": str(pdf_file)},
        )
        assert shared_res.status_code == 201

        extra_file = tmp_path / "notes.txt"
        extra_file.write_text("keep me", encoding="utf-8")
        extra_res = client.post(
            f"/api/entries/{second_entry['id']}/resources",
            json={"path": str(extra_file)},
        )
        assert extra_res.status_code == 201

        preview = client.post(
            "/api/resources/delete/preview",
            json={"resource_ids": [pdf_res.json()["id"]]},
        )
        assert preview.status_code == 200
        preview_body = preview.json()
        assert preview_body["has_shared_files"] is True
        assert preview_body["total_affected_links"] == 2
        assert len(preview_body["items"][0]["affected_entries"]) == 2

        unconfirmed = client.post(
            "/api/resources/delete",
            json={"resource_ids": [pdf_res.json()["id"]], "confirmed": False},
        )
        assert unconfirmed.status_code == 400
        assert unconfirmed.json()["code"] == "RESOURCE_DELETE_CONFIRM_REQUIRED"

        unacknowledged = client.post(
            "/api/resources/delete",
            json={
                "resource_ids": [pdf_res.json()["id"]],
                "confirmed": True,
                "acknowledge_shared": False,
            },
        )
        assert unacknowledged.status_code == 409
        assert unacknowledged.json()["code"] == "RESOURCE_SHARED_CONFIRM_REQUIRED"
        assert pdf_file.is_file()

        deleted = client.post(
            "/api/resources/delete",
            json={
                "resource_ids": [pdf_res.json()["id"]],
                "confirmed": True,
                "acknowledge_shared": True,
            },
        )
        assert deleted.status_code == 200
        assert deleted.json()["recycled_count"] == 1
        assert len(recycled_paths) == 1
        assert not pdf_file.exists()

        # 未勾选的 extra_file 及其关联必须保留。
        remaining = client.get(f"/api/entries/{second_entry['id']}/resources").json()
        assert remaining["total"] == 1
        assert remaining["items"][0]["id"] == extra_res.json()["id"]
        assert extra_file.read_text(encoding="utf-8") == "keep me"
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_system_recycle_bin_validates_paths_and_invokes_win32(tmp_path, monkeypatch) -> None:
    import sys

    from app.adapters.recycle_bin import RecycleBinError, SystemRecycleBin

    mover = SystemRecycleBin()
    with pytest.raises(RecycleBinError):
        mover.move(tmp_path / "missing.bin")
    with pytest.raises(RecycleBinError):
        mover.move(tmp_path)

    target = tmp_path / "recycle_me.txt"
    target.write_text("recycle", encoding="utf-8")
    called = []

    def fake_win_recycle(path) -> None:
        called.append(path)
        path.unlink()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "app.adapters.recycle_bin._move_to_windows_recycle_bin",
        fake_win_recycle,
    )
    mover.move(target)
    assert called == [target.resolve()]
    assert not target.exists()
