"""资源关联、文件状态和元数据业务服务。"""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.adapters.system_open import SystemDefaultOpener, SystemOpenError
from app.application.errors import (
    NotFoundError,
    ResourceAccessDeniedError,
    ResourceAlreadyLinkedError,
    ResourceFileMissingError,
    ResourceLinkNotFoundError,
    ResourceNotFileError,
    ResourceNotFoundError,
    ResourceOpenFailedError,
    ResourcePathNotAbsoluteError,
)
from app.application.ports import EntryRepository, ResourceOpener, ResourceRepository
from app.domain.entry import ResourceCreate, ResourceRead


class ResourceService:
    def __init__(
        self,
        entry_repository: EntryRepository,
        resource_repository: ResourceRepository,
        opener: ResourceOpener | None = None,
    ) -> None:
        self.entry_repository = entry_repository
        self.resource_repository = resource_repository
        self.opener = opener or SystemDefaultOpener()

    def list_resources(self, entry_id: int) -> list[ResourceRead]:
        self._require_entry(entry_id)
        return self.resource_repository.list_by_entry(entry_id)

    def attach_resource(
        self,
        entry_id: int,
        payload: ResourceCreate,
    ) -> ResourceRead:
        self._require_entry(entry_id)
        path = self._normalize_path(payload.path)

        try:
            stat = path.stat()
        except FileNotFoundError as exc:
            raise ResourceFileMissingError("资源文件不存在") from exc
        except PermissionError as exc:
            raise ResourceAccessDeniedError("无法访问资源文件") from exc
        except OSError as exc:
            raise ResourceAccessDeniedError("无法读取资源文件信息") from exc

        if not path.is_file():
            raise ResourceNotFileError("资源路径不是普通文件")

        normalized_path = str(path)
        duplicate = self.resource_repository.find_by_entry_path(
            entry_id,
            normalized_path,
        )
        if duplicate is not None:
            raise ResourceAlreadyLinkedError("该条目已经关联此文件")

        try:
            digest = self._sha256(path)
        except PermissionError as exc:
            raise ResourceAccessDeniedError("无法读取资源文件") from exc
        except OSError as exc:
            raise ResourceAccessDeniedError("无法计算资源文件哈希") from exc

        created = self.resource_repository.create(
            share_id=str(uuid4()),
            entry_id=entry_id,
            path=normalized_path,
            file_name=path.name,
            extension=path.suffix.lower(),
            size_bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            sha256=digest,
            availability="present",
            created_at=datetime.now(timezone.utc),
        )
        return created.data

    def detach_resource(self, entry_id: int, resource_id: int) -> None:
        self._require_entry(entry_id)
        resource = self.resource_repository.get(resource_id)
        if resource is None:
            raise ResourceNotFoundError("资源不存在")
        if resource.data.entry_id != entry_id:
            raise ResourceLinkNotFoundError("该资源没有关联到此条目")

        deleted = self.resource_repository.delete(entry_id, resource_id)
        if not deleted:
            raise ResourceLinkNotFoundError("该资源没有关联到此条目")

    def recheck_resource(self, resource_id: int) -> tuple[ResourceRead, bool]:
        resource = self.resource_repository.get(resource_id)
        if resource is None:
            raise ResourceNotFoundError("资源不存在")

        path = Path(resource.path)
        previous = resource.data

        try:
            stat = path.stat()
            is_file = path.is_file()
        except PermissionError as exc:
            raise ResourceAccessDeniedError("无法访问资源文件") from exc
        except (FileNotFoundError, NotADirectoryError):
            is_file = False
            stat = None
        except OSError as exc:
            raise ResourceAccessDeniedError("无法检测资源文件") from exc

        if not is_file or stat is None:
            updated = self.resource_repository.update(
                resource_id,
                {
                    "availability": "missing",
                    "size_bytes": None,
                    "mtime_ns": None,
                    "sha256": None,
                },
            )
            if updated is None:
                raise ResourceNotFoundError("资源不存在")
            return updated.data, previous.availability != "missing"

        try:
            digest = self._sha256(path)
        except PermissionError as exc:
            raise ResourceAccessDeniedError("无法读取资源文件") from exc
        except OSError as exc:
            raise ResourceAccessDeniedError("无法计算资源文件哈希") from exc

        changed = (
            previous.availability != "present"
            or previous.size_bytes != stat.st_size
            or previous.mtime_ns != stat.st_mtime_ns
            or previous.sha256 != digest
        )
        updated = self.resource_repository.update(
            resource_id,
            {
                "availability": "present",
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": digest,
            },
        )
        if updated is None:
            raise ResourceNotFoundError("资源不存在")
        return updated.data, changed

    def resolve_path(self, resource_id: int) -> Path:
        """根据资源 ID 解析并校验内部保存的本地路径。"""
        resource = self.resource_repository.get(resource_id)
        if resource is None:
            raise ResourceNotFoundError("资源不存在")

        path = Path(resource.path)
        if not path.is_absolute():
            raise ResourcePathNotAbsoluteError("资源路径必须是绝对路径")

        try:
            path.stat()
        except FileNotFoundError as exc:
            raise ResourceFileMissingError("资源文件不存在") from exc
        except PermissionError as exc:
            raise ResourceAccessDeniedError("无法访问资源文件") from exc
        except OSError as exc:
            raise ResourceAccessDeniedError("无法读取资源文件信息") from exc

        if not path.is_file():
            raise ResourceNotFileError("资源路径不是普通文件")
        return path

    def open_resource(self, resource_id: int) -> None:
        """打开资源对应的文件，不接受任意前端路径。"""
        path = self.resolve_path(resource_id)
        try:
            self.opener.open(path)
        except SystemOpenError as exc:
            raise ResourceOpenFailedError("系统默认程序无法打开资源") from exc
        except (FileNotFoundError, PermissionError, OSError) as exc:
            raise ResourceOpenFailedError("系统默认程序无法打开资源") from exc

    def _require_entry(self, entry_id: int) -> None:
        if self.entry_repository.get(entry_id) is None:
            raise NotFoundError(f"条目 {entry_id} 不存在")

    @staticmethod
    def _normalize_path(raw_path: str) -> Path:
        path = Path(raw_path.strip())
        if not path.is_absolute():
            raise ResourcePathNotAbsoluteError("资源路径必须是绝对路径")

        try:
            return path.resolve(strict=False)
        except OSError as exc:
            raise ResourceAccessDeniedError("无法规范化资源路径") from exc

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
