"""资源关联、文件状态、共享引用检测和安全回收站删除服务。"""

from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.adapters.recycle_bin import RecycleBinError, SystemRecycleBin
from app.adapters.system_open import SystemDefaultOpener, SystemOpenError
from app.application.errors import (
    EntryNotFoundError,
    ResourceAccessDeniedError,
    ResourceAlreadyLinkedError,
    ResourceDeleteConfirmRequiredError,
    ResourceFileMissingError,
    ResourceLinkNotFoundError,
    ResourceNotFileError,
    ResourceNotFoundError,
    ResourceOpenFailedError,
    ResourcePathNotAbsoluteError,
    ResourceRecycleFailedError,
    ResourceSharedConfirmRequiredError,
)
from app.application.ports import (
    EntryRepository,
    FileTypeDetector,
    RecycleBinMover,
    ResourceOpener,
    ResourceRepository,
)
from app.db.records import StoredResource
from app.domain.entry import (
    EntryRead,
    EntryType,
    LifecycleState,
    ResourceCreate,
    ResourceDeletePreview,
    ResourceDeletePreviewItem,
    ResourceDeleteRequest,
    ResourceDeleteResult,
    ResourceRead,
    ResourceSharedEntryRef,
)


class ResourceService:
    def __init__(
        self,
        entry_repository: EntryRepository,
        resource_repository: ResourceRepository,
        opener: ResourceOpener | None = None,
        type_detector: FileTypeDetector | None = None,
        recycle_bin: RecycleBinMover | None = None,
    ) -> None:
        self.entry_repository = entry_repository
        self.resource_repository = resource_repository
        self.opener = opener or SystemDefaultOpener()
        self.type_detector = type_detector
        self.recycle_bin = recycle_bin or SystemRecycleBin()

    def list_resources(self, entry_id: int) -> list[ResourceRead]:
        self._require_entry(entry_id)
        return self.resource_repository.list_by_entry(entry_id)

    def attach_resource(
        self,
        entry_id: int,
        payload: ResourceCreate,
    ) -> ResourceRead:
        entry = self._require_entry(entry_id)
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

        detected_type = self._detect_entry_type(path)
        now = datetime.now(timezone.utc)

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
            created_at=now,
        )

        # 仅当条目处于未归类 OTHER 且文件识别出具体类型时自动补齐，不覆盖用户显式指定的作品类型。
        if (
            detected_type is not None
            and entry.type == EntryType.OTHER
            and detected_type != EntryType.OTHER
        ):
            self.entry_repository.update(
                entry_id,
                {"type": detected_type, "updated_at": now},
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

    def preview_delete_resources(
        self,
        resource_ids: list[int],
    ) -> ResourceDeletePreview:
        """在执行回收站删除前预览所选文件及跨条目共享引用影响，不改动磁盘或数据库。"""
        selected = self._load_resources(resource_ids)
        items: list[ResourceDeletePreviewItem] = []
        unique_paths: set[str] = set()
        affected_resource_ids: set[int] = set()

        for stored in selected:
            unique_paths.add(stored.path)
            links, refs = self._collect_path_references(stored.path)
            for link in links:
                affected_resource_ids.add(link.data.id)
            shared = len({ref.entry_id for ref in refs}) > 1
            items.append(
                ResourceDeletePreviewItem(
                    resource_id=stored.data.id,
                    entry_id=stored.data.entry_id,
                    file_name=stored.data.file_name,
                    extension=stored.data.extension,
                    size_bytes=stored.data.size_bytes,
                    availability=stored.data.availability,
                    shared=shared,
                    affected_entries=refs,
                )
            )

        return ResourceDeletePreview(
            items=items,
            has_shared_files=any(item.shared for item in items),
            total_files=len(unique_paths),
            total_affected_links=len(affected_resource_ids),
        )

    def delete_resources_to_recycle_bin(
        self,
        payload: ResourceDeleteRequest,
    ) -> ResourceDeleteResult:
        """经二次确认与共享确认后，按勾选资源将物理文件移入系统回收站并清理库记录。"""
        if not payload.confirmed:
            raise ResourceDeleteConfirmRequiredError("删除磁盘文件前必须经过二次确认")

        selected = self._load_resources(payload.resource_ids)

        ordered_paths: list[str] = []
        links_by_path: dict[str, list[StoredResource]] = {}
        refs_by_path: dict[str, list[ResourceSharedEntryRef]] = {}

        for stored in selected:
            if stored.path not in links_by_path:
                ordered_paths.append(stored.path)
                links, refs = self._collect_path_references(stored.path)
                links_by_path[stored.path] = links
                refs_by_path[stored.path] = refs

        shared_conflicts = []
        for raw_path in ordered_paths:
            refs = refs_by_path[raw_path]
            if len({ref.entry_id for ref in refs}) > 1:
                representative = links_by_path[raw_path][0].data
                shared_conflicts.append(
                    {
                        "resource_id": representative.id,
                        "file_name": representative.file_name,
                        "affected_entries": [ref.model_dump() for ref in refs],
                    }
                )

        if shared_conflicts and not payload.acknowledge_shared:
            raise ResourceSharedConfirmRequiredError(
                "所选文件被多个条目共享引用，请先确认共享影响后再移入回收站",
                details={"shared_resources": shared_conflicts},
            )

        validated_paths: list[tuple[str, Path]] = []
        for raw_path in ordered_paths:
            validated_paths.append((raw_path, self._validate_existing_file(raw_path)))

        deleted_resource_ids: list[int] = []
        affected_entry_ids: set[int] = set()

        for raw_path, resolved_path in validated_paths:
            try:
                self.recycle_bin.move(resolved_path)
            except (RecycleBinError, OSError) as exc:
                raise ResourceRecycleFailedError("无法将资源文件移入系统回收站") from exc

            path_links = links_by_path[raw_path]
            ids_to_remove = [item.data.id for item in path_links]
            self.resource_repository.delete_by_ids(ids_to_remove)
            deleted_resource_ids.extend(ids_to_remove)
            for item in path_links:
                affected_entry_ids.add(item.data.entry_id)

        return ResourceDeleteResult(
            deleted_resource_ids=sorted(set(deleted_resource_ids)),
            affected_entry_ids=sorted(affected_entry_ids),
            recycled_count=len(validated_paths),
        )

    def resolve_path(self, resource_id: int) -> Path:
        """根据资源 ID 解析并校验内部保存的本地路径。"""
        resource = self.resource_repository.get(resource_id)
        if resource is None:
            raise ResourceNotFoundError("资源不存在")

        return self._validate_existing_file(resource.path)

    def open_resource(
        self,
        resource_id: int,
        *,
        confirm_open: Callable[[Path], bool] | None = None,
    ) -> None:
        """打开已经解析的资源。确认回调拒绝时不启动文件。"""
        path = self.resolve_path(resource_id)
        if confirm_open is not None and not confirm_open(path):
            return
        try:
            self.opener.open(path)
        except SystemOpenError as exc:
            raise ResourceOpenFailedError("系统默认程序无法打开资源") from exc
        except (FileNotFoundError, PermissionError, OSError) as exc:
            raise ResourceOpenFailedError("系统默认程序无法打开资源") from exc

    def _require_entry(self, entry_id: int) -> EntryRead:
        entry = self.entry_repository.get(entry_id)
        if entry is None:
            raise EntryNotFoundError(
                f"条目 {entry_id} 不存在",
                details={"entry_id": entry_id},
            )
        return entry

    def _load_resources(self, resource_ids: list[int]) -> list[StoredResource]:
        loaded: list[StoredResource] = []
        seen: set[int] = set()
        for resource_id in resource_ids:
            if resource_id in seen:
                continue
            seen.add(resource_id)
            stored = self.resource_repository.get(resource_id)
            if stored is None:
                raise ResourceNotFoundError(
                    f"资源 {resource_id} 不存在",
                    details={"resource_id": resource_id},
                )
            loaded.append(stored)
        return loaded

    def _collect_path_references(
        self,
        path: str,
    ) -> tuple[list[StoredResource], list[ResourceSharedEntryRef]]:
        links = self.resource_repository.list_by_path(path)
        refs: list[ResourceSharedEntryRef] = []
        for link in links:
            entry = self.entry_repository.get(link.data.entry_id)
            if entry is None or entry.lifecycle_state != LifecycleState.LIBRARY:
                continue
            refs.append(
                ResourceSharedEntryRef(
                    entry_id=entry.id,
                    entry_title=entry.title,
                    resource_id=link.data.id,
                )
            )
        return links, refs

    def _detect_entry_type(self, path: Path) -> EntryType | None:
        if self.type_detector is None:
            return None
        try:
            detected = self.type_detector.detect(path)
            raw_value = detected.value if hasattr(detected, "value") else str(detected)
            return EntryType(raw_value)
        except Exception:
            return EntryType.OTHER

    @staticmethod
    def _validate_existing_file(raw_path: str) -> Path:
        path = Path(raw_path)
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
