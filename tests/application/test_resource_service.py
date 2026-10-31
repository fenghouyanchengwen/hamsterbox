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
    ResourcePathNotAbsoluteError,
)
from app.application.resource_service import ResourceService
from app.db.base import Base
from app.db.entry_repository import SqliteEntryRepository
from app.db.resource_repository import SqliteResourceRepository
from app.domain.entry import EntryCreate, EntryType, ResourceCreate


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
