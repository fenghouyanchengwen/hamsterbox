from hashlib import sha256

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.entry_service import EntryService
from app.application.errors import (
    ResourceAlreadyLinkedError,
    ResourceFileMissingError,
    ResourceNotFileError,
    ResourceNotFoundError,
    ResourceOpenFailedError,
    ResourcePathNotAbsoluteError,
)
from app.application.resource_service import ResourceService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.domain.entry import EntryCreate, EntryType, ResourceCreate


class RecordingOpener:
    def __init__(self) -> None:
        self.paths = []

    def open(self, path) -> None:
        self.paths.append(path)


class FailingOpener:
    def open(self, path) -> None:
        raise OSError("default program unavailable")


@pytest.fixture
def services() -> tuple[EntryService, ResourceService]:
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
    yield (
        EntryService(entry_repository),
        ResourceService(entry_repository, resource_repository),
    )
    session.close()


def test_attach_resource_reads_metadata_and_hash(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )
    file_path = tmp_path / "Example.MP3"
    content = b"hamsterbox"
    file_path.write_bytes(content)

    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(file_path)),
    )

    assert resource.entry_id == entry.id
    assert resource.file_name == "Example.MP3"
    assert resource.extension == ".mp3"
    assert resource.size_bytes == len(content)
    assert resource.sha256 == sha256(content).hexdigest()
    assert resource.availability == "present"
    assert str(file_path) not in resource.model_dump_json()


def test_duplicate_resource_is_rejected(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")
    payload = ResourceCreate(path=str(file_path))

    resource_service.attach_resource(entry.id, payload)

    with pytest.raises(ResourceAlreadyLinkedError):
        resource_service.attach_resource(entry.id, payload)


def test_invalid_paths_are_rejected(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )

    with pytest.raises(ResourcePathNotAbsoluteError):
        resource_service.attach_resource(entry.id, ResourceCreate(path="a.txt"))

    with pytest.raises(ResourceFileMissingError):
        resource_service.attach_resource(
            entry.id,
            ResourceCreate(path=str(tmp_path / "missing.txt")),
        )

    directory = tmp_path / "folder"
    directory.mkdir()
    with pytest.raises(ResourceNotFileError):
        resource_service.attach_resource(
            entry.id,
            ResourceCreate(path=str(directory)),
        )


def test_recheck_missing_file_and_detach_keep_disk_file(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")
    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(file_path)),
    )

    file_path.unlink()
    rechecked, changed = resource_service.recheck_resource(resource.id)
    assert changed is True
    assert rechecked.availability == "missing"

    # 资源已经失效，解除数据库关联仍然不会操作磁盘路径。
    resource_service.detach_resource(entry.id, resource.id)
    assert not file_path.exists()


def test_open_resource_resolves_path_and_uses_system_opener(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")
    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(file_path)),
    )
    opener = RecordingOpener()
    resource_service.opener = opener

    resource_service.open_resource(resource.id)

    assert opener.paths == [file_path.resolve()]


def test_open_resource_rejects_missing_resource_and_deleted_file(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")
    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(file_path)),
    )

    with pytest.raises(ResourceNotFoundError):
        resource_service.open_resource(99999)

    file_path.unlink()
    with pytest.raises(ResourceFileMissingError):
        resource_service.open_resource(resource.id)


def test_open_resource_rejects_directory_and_maps_opener_failure(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    entry_service, resource_service = services
    entry = entry_service.create_entry(
        EntryCreate(title="示例", type=EntryType.GAME)
    )
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")
    resource = resource_service.attach_resource(
        entry.id,
        ResourceCreate(path=str(file_path)),
    )

    file_path.unlink()
    file_path.mkdir()
    with pytest.raises(ResourceNotFileError):
        resource_service.open_resource(resource.id)

    file_path.rmdir()
    file_path.write_text("hello", encoding="utf-8")
    resource_service.opener = FailingOpener()
    with pytest.raises(ResourceOpenFailedError):
        resource_service.open_resource(resource.id)


def test_attach_resource_detects_type_only_for_unclassified_entries(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    from app.adapters.enums import EntryType as AdapterEntryType
    from app.application.errors import (
        ResourceDeleteConfirmRequiredError,
        ResourceRecycleFailedError,
        ResourceSharedConfirmRequiredError,
    )
    from app.domain.entry import ResourceDeleteRequest

    class FakeDetector:
        def detect(self, path):
            if path.suffix.lower() == ".epub":
                return AdapterEntryType.BOOK
            if path.suffix.lower() == ".png":
                return AdapterEntryType.IMAGE
            return AdapterEntryType.OTHER

    entry_service, resource_service = services
    resource_service.type_detector = FakeDetector()

    unclassified = entry_service.create_entry(
        EntryCreate(title="待识别作品", type=EntryType.OTHER)
    )
    epub_file = tmp_path / "novel.epub"
    epub_file.write_bytes(b"epub-bytes")
    resource_service.attach_resource(unclassified.id, ResourceCreate(path=str(epub_file)))
    assert entry_service.get_entry(unclassified.id).type == EntryType.BOOK

    # 已明确指定为 GAME 的条目，挂载附加图片时不能覆盖原有作品类型（契约 §4 第2条）。
    game_entry = entry_service.create_entry(
        EntryCreate(title="塞尔达", type=EntryType.GAME)
    )
    cover_file = tmp_path / "poster.png"
    cover_file.write_bytes(b"png-bytes")
    resource_service.attach_resource(game_entry.id, ResourceCreate(path=str(cover_file)))
    assert entry_service.get_entry(game_entry.id).type == EntryType.GAME

    # 检测器异常时必须安全降级，不阻断资源关联。
    class BrokenDetector:
        def detect(self, path):
            raise RuntimeError("boom")

    resource_service.type_detector = BrokenDetector()
    unknown = tmp_path / "mystery.xyz"
    unknown.write_bytes(b"xyz")
    attached = resource_service.attach_resource(
        game_entry.id, ResourceCreate(path=str(unknown))
    )
    assert attached.availability == "present"
    _ = (
        ResourceDeleteConfirmRequiredError,
        ResourceRecycleFailedError,
        ResourceSharedConfirmRequiredError,
        ResourceDeleteRequest,
    )


def test_recycle_bin_delete_per_file_and_shared_reference_guard(
    tmp_path,
    services: tuple[EntryService, ResourceService],
) -> None:
    from app.adapters.recycle_bin import RecycleBinError
    from app.application.errors import (
        ResourceDeleteConfirmRequiredError,
        ResourceRecycleFailedError,
        ResourceSharedConfirmRequiredError,
    )
    from app.domain.entry import ResourceDeleteRequest

    class FakeRecycleBin:
        def __init__(self) -> None:
            self.recycled: list = []
            self.should_fail = False

        def move(self, path) -> None:
            if self.should_fail:
                raise RecycleBinError("simulated failure")
            self.recycled.append(path)
            path.unlink()

    entry_service, resource_service = services
    recycle_bin = FakeRecycleBin()
    resource_service.recycle_bin = recycle_bin

    # B1-A01：同一条目挂两个文件，只勾选其中一个删除。
    entry_a = entry_service.create_entry(EntryCreate(title="条目A", type=EntryType.VIDEO))
    file_one = tmp_path / "part1.mp4"
    file_two = tmp_path / "part2.mp4"
    file_one.write_bytes(b"video-part-1")
    file_two.write_bytes(b"video-part-2")

    res_one = resource_service.attach_resource(entry_a.id, ResourceCreate(path=str(file_one)))
    res_two = resource_service.attach_resource(entry_a.id, ResourceCreate(path=str(file_two)))

    # 未二次确认必须拒绝，原文件与库记录不动。
    with pytest.raises(ResourceDeleteConfirmRequiredError):
        resource_service.delete_resources_to_recycle_bin(
            ResourceDeleteRequest(resource_ids=[res_one.id], confirmed=False)
        )
    assert file_one.is_file()
    assert len(resource_service.list_resources(entry_a.id)) == 2

    # 确认删除 file_one，file_two 与其关联保留。
    result = resource_service.delete_resources_to_recycle_bin(
        ResourceDeleteRequest(resource_ids=[res_one.id], confirmed=True)
    )
    assert result.recycled_count == 1
    assert result.deleted_resource_ids == [res_one.id]
    assert not file_one.exists()
    assert file_two.read_bytes() == b"video-part-2"
    assert [r.id for r in resource_service.list_resources(entry_a.id)] == [res_two.id]

    # B1-A02：两个条目共享同一文件，预览返回共享提示，未确认共享前拒绝删除。
    entry_b = entry_service.create_entry(EntryCreate(title="条目B", type=EntryType.VIDEO))
    res_two_shared = resource_service.attach_resource(
        entry_b.id, ResourceCreate(path=str(file_two))
    )

    preview = resource_service.preview_delete_resources([res_two.id])
    assert preview.has_shared_files is True
    assert preview.items[0].shared is True
    assert [ref.entry_title for ref in preview.items[0].affected_entries] == ["条目A", "条目B"]

    with pytest.raises(ResourceSharedConfirmRequiredError) as exc_info:
        resource_service.delete_resources_to_recycle_bin(
            ResourceDeleteRequest(
                resource_ids=[res_two.id],
                confirmed=True,
                acknowledge_shared=False,
            )
        )
    assert exc_info.value.details["shared_resources"][0]["file_name"] == "part2.mp4"
    assert file_two.is_file()

    # 回收站底层失败时不清理数据库记录。
    recycle_bin.should_fail = True
    with pytest.raises(ResourceRecycleFailedError):
        resource_service.delete_resources_to_recycle_bin(
            ResourceDeleteRequest(
                resource_ids=[res_two.id],
                confirmed=True,
                acknowledge_shared=True,
            )
        )
    assert len(resource_service.list_resources(entry_a.id)) == 1
    assert len(resource_service.list_resources(entry_b.id)) == 1

    # 恢复正常并显式确认共享后，物理文件只移入回收站一次，两条数据库关联一并移除。
    recycle_bin.should_fail = False
    shared_result = resource_service.delete_resources_to_recycle_bin(
        ResourceDeleteRequest(
            resource_ids=[res_two.id],
            confirmed=True,
            acknowledge_shared=True,
        )
    )
    assert shared_result.recycled_count == 1
    assert shared_result.deleted_resource_ids == sorted([res_two.id, res_two_shared.id])
    assert shared_result.affected_entry_ids == sorted([entry_a.id, entry_b.id])
    assert resource_service.list_resources(entry_a.id) == []
    assert resource_service.list_resources(entry_b.id) == []
