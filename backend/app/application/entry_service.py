from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.application.errors import (
    EntryNotFoundError,
    EntryReviewTooLongError,
    InvalidEntryLifecycleError,
    ResourceAccessDeniedError,
    ResourceFileMissingError,
    ResourceNotFileError,
    ResourceNotFoundError,
    ResourcePathNotAbsoluteError,
)
from app.application.ports import EntryRepository, ResourceRepository
from app.domain.entry import (
    EntryCreate,
    EntryDetail,
    EntryRead,
    EntryUpdate,
    LifecycleState,
)

MAX_REVIEW_LENGTH = 10_000
_UNSET = object()


class EntryService:
    def __init__(
        self,
        repository: EntryRepository,
        resource_repository: ResourceRepository | None = None,
    ) -> None:
        self.repository = repository
        self.resource_repository = resource_repository

    def create_entry(self, payload: EntryCreate) -> EntryRead:
        return self._create_with_state(payload, LifecycleState.LIBRARY)

    def create_temporary_entry(
        self,
        payload: EntryCreate,
        *,
        source_resource_ids: list[int] | None = None,
    ) -> EntryRead | EntryDetail:
        """为部分资源分享流程创建隐藏的 temporary 派生条目，不修改原条目。"""
        source_resources = []
        if source_resource_ids:
            if self.resource_repository is None:
                raise InvalidEntryLifecycleError("当前条目服务未配置资源仓储")
            seen: set[int] = set()
            for rid in source_resource_ids:
                if rid in seen:
                    continue
                seen.add(rid)
                stored = self.resource_repository.get(rid)
                if stored is None:
                    raise ResourceNotFoundError(
                        f"资源 {rid} 不存在",
                        details={"resource_id": rid},
                    )
                source_resources.append(stored)

        created = self._create_with_state(payload, LifecycleState.TEMPORARY)

        if source_resources and self.resource_repository is not None:
            now = datetime.now(timezone.utc)
            copied = []
            for stored in source_resources:
                item = self.resource_repository.create(
                    share_id=str(uuid4()),
                    entry_id=created.id,
                    path=stored.path,
                    file_name=stored.data.file_name,
                    extension=stored.data.extension,
                    size_bytes=stored.data.size_bytes or 0,
                    mtime_ns=stored.data.mtime_ns or 0,
                    sha256=stored.data.sha256 or "",
                    availability=stored.data.availability,
                    created_at=now,
                )
                copied.append(item.data)
            return EntryDetail(**created.model_dump(), resources=copied)

        if self.resource_repository is not None:
            return EntryDetail(**created.model_dump(), resources=[])
        return created

    def promote_temporary_entry(
        self,
        entry_id: int,
        *,
        review: str | None | object = _UNSET,
    ) -> EntryRead:
        """分享成功后将 temporary 派生条目保存为正式 library 条目。"""
        entry = self._require_entry(entry_id)
        if entry.lifecycle_state != LifecycleState.TEMPORARY:
            raise InvalidEntryLifecycleError(
                f"条目 {entry_id} 不是临时派生条目，不能执行转正",
                details={"entry_id": entry_id, "lifecycle_state": entry.lifecycle_state.value},
            )

        values: dict[str, object] = {
            "lifecycle_state": LifecycleState.LIBRARY,
            "updated_at": datetime.now(timezone.utc),
        }
        if review is not _UNSET:
            assert review is None or isinstance(review, str)
            self._validate_review(review)
            values["review"] = review

        updated = self.repository.update(entry_id, values)
        if updated is None:
            raise EntryNotFoundError(
                f"条目 {entry_id} 不存在",
                details={"entry_id": entry_id},
            )
        return updated

    def discard_temporary_entry(self, entry_id: int) -> None:
        """分享取消、失败或选择删除时清理 temporary 派生条目，保护正式条目。"""
        entry = self._require_entry(entry_id)
        if entry.lifecycle_state != LifecycleState.TEMPORARY:
            raise InvalidEntryLifecycleError(
                f"条目 {entry_id} 是正式库条目，不能作为临时条目清理",
                details={"entry_id": entry_id, "lifecycle_state": entry.lifecycle_state.value},
            )
        if not self.repository.delete(entry_id):
            raise EntryNotFoundError(
                f"条目 {entry_id} 不存在",
                details={"entry_id": entry_id},
            )

    def get_entry(self, entry_id: int) -> EntryRead | EntryDetail:
        entry = self._require_entry(entry_id)

        if self.resource_repository is None:
            return entry

        resources = self.resource_repository.list_by_entry(entry_id)
        return EntryDetail(**entry.model_dump(), resources=resources)

    def update_entry(
        self,
        entry_id: int,
        payload: EntryUpdate,
    ) -> EntryRead:
        self._require_entry(entry_id)

        values = payload.model_dump(exclude_unset=True)
        if "review" in values:
            self._validate_review(values["review"])
        if "cover_path" in values:
            values["cover_path"] = self._validate_cover_path(values["cover_path"])
        values["updated_at"] = datetime.now(timezone.utc)

        updated = self.repository.update(entry_id, values)

        if updated is None:
            raise EntryNotFoundError(
                f"条目 {entry_id} 不存在",
                details={"entry_id": entry_id},
            )

        return updated

    def remove_entry(self, entry_id: int) -> None:
        self._require_entry(entry_id)

        deleted = self.repository.delete(entry_id)

        if not deleted:
            raise EntryNotFoundError(
                f"条目 {entry_id} 不存在",
                details={"entry_id": entry_id},
            )

    def _create_with_state(
        self,
        payload: EntryCreate,
        lifecycle_state: LifecycleState,
    ) -> EntryRead:
        self._validate_review(payload.review)
        cover_path = self._validate_cover_path(payload.cover_path)
        now = datetime.now(timezone.utc)

        return self.repository.create(
            share_id=str(uuid4()),
            title=payload.title,
            entry_type=payload.type,
            description=payload.description,
            cover_path=cover_path,
            review=payload.review,
            lifecycle_state=lifecycle_state,
            created_at=now,
            updated_at=now,
        )

    def _require_entry(self, entry_id: int) -> EntryRead:
        entry = self.repository.get(entry_id)
        if entry is None:
            raise EntryNotFoundError(
                f"条目 {entry_id} 不存在",
                details={"entry_id": entry_id},
            )
        return entry

    @staticmethod
    def _validate_review(review: str | None) -> None:
        if review is not None and len(review) > MAX_REVIEW_LENGTH:
            raise EntryReviewTooLongError(
                f"整体评价最多 {MAX_REVIEW_LENGTH} 个字符",
                details={"field": "review", "max_length": MAX_REVIEW_LENGTH},
            )

    @staticmethod
    def _validate_cover_path(raw_path: str | None) -> str | None:
        if raw_path is None:
            return None
        cleaned = raw_path.strip()
        if not cleaned:
            return None

        path = Path(cleaned)
        if not path.is_absolute():
            raise ResourcePathNotAbsoluteError("封面路径必须是绝对路径")

        try:
            resolved = path.resolve(strict=False)
            resolved.stat()
        except FileNotFoundError as exc:
            raise ResourceFileMissingError("封面文件不存在") from exc
        except PermissionError as exc:
            raise ResourceAccessDeniedError("无法访问封面文件") from exc
        except OSError as exc:
            raise ResourceAccessDeniedError("无法读取封面文件信息") from exc

        if not resolved.is_file():
            raise ResourceNotFileError("封面路径不是普通文件")

        return str(resolved)
