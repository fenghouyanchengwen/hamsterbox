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

