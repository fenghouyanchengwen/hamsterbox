"""预览并导入分享包元数据，基于接收方已登记的文件完成匹配。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import stat
from uuid import UUID

from app.application.errors import CodedApplicationError
from app.application.share_export import ShareExportError, fingerprint_file
from app.application.share_preview import preview_share_package
from app.db.share_import_repository import ShareImportRepository
from app.db.records import normalize_tag_name


class ShareImportSelectionError(CodedApplicationError):
    code = "SHARE_IMPORT_SELECTION_INVALID"
    status_code = 422


class ShareImportConflictError(CodedApplicationError):
    code = "SHARE_IMPORT_CONFLICT"
    status_code = 409


@dataclass(frozen=True)
class VerifiedFile:
    path: Path
    size: int
    mtime_ns: int
    digest: str


@dataclass(frozen=True)
class ResourceMatch:
    share_id: str
    status: str
    candidates: tuple[VerifiedFile, ...] = ()

    def to_response(self) -> dict:
        return {
            "share_id": self.share_id,
            "status": self.status,
            "candidate_count": len(self.candidates),
        }


def _tag_categories(repository: ShareImportRepository, entries: list[dict], assignments: list[str]) -> dict[str, int]:
    known_refs = {tag["tag_ref"] for entry in entries for tag in entry["tags"]}
    targets = {}
    for assignment in assignments:
        ref, _, category = assignment.partition(":")
        try:
            ref = str(UUID(ref))
            category_id = int(category)
        except ValueError as exc:
            raise ShareImportSelectionError("标签分类选择格式无效") from exc
        if ref not in known_refs or ref in targets or not 0 < category_id < 2**63:
            raise ShareImportSelectionError("标签或目标分类无效，或标签选择重复")
        if repository.categories.get(category_id) is None:
            raise ShareImportSelectionError("所选标签分类不存在")
        targets[ref] = category_id
    return targets


def _ratings(entry: dict, categories: dict[str, int], default_category: int | None) -> tuple[dict, list[str]]:
    names = {tag["tag_ref"]: tag["name"].strip() for tag in entry["tags"]}
    ratings = {}
    conflicts = set()
    for relation in entry["entry_tags"]:
        ref = relation["tag_ref"]
        name = names[ref]
        category = categories.get(ref, default_category)
        key = (category, normalize_tag_name(name))
        if key in ratings and ratings[key][1] != relation["rating"]:
            conflicts.add(name)
        ratings[key] = (name, relation["rating"])
    return ratings, sorted(conflicts)


def _verified_candidates(repository: ShareImportRepository, digest: str) -> tuple[VerifiedFile, ...]:
    verified = {}
    for path in repository.resource_paths_for_hash(digest):
        if not Path(path).is_absolute():
            continue
        try:
            resolved = Path(path).resolve(strict=True)
            size, mtime_ns, current_digest = fingerprint_file(str(resolved))
        except (OSError, RuntimeError, ShareExportError):
            continue
        if current_digest == digest:
            verified[resolved] = VerifiedFile(resolved, size, mtime_ns, digest)
    return tuple(verified.values())


def _resource_matches(repository: ShareImportRepository, entries: list[dict]) -> dict[str, list[ResourceMatch]]:
    candidates_by_digest = {}
    by_entry = {}
    for entry in entries:
        used_paths = set()
        matches = []
        for resource in entry["resources"]:
            share_id, digest = resource["share_id"], resource["sha256"]
            if repository.has_resource(share_id):
                matches.append(ResourceMatch(share_id, "conflict"))
                continue
            if digest is None:
                matches.append(ResourceMatch(share_id, "missing"))
                continue
            if digest not in candidates_by_digest:
                candidates_by_digest[digest] = _verified_candidates(repository, digest)
            candidates = candidates_by_digest[digest]
            if resource["size_bytes"] is not None:
                candidates = tuple(candidate for candidate in candidates if candidate.size == resource["size_bytes"])
            if len(candidates) != 1:
                status = "needs_selection" if candidates else "missing"
            elif candidates[0].path in used_paths:
                status = "conflict"
            else:
                status = "auto_linked"
                used_paths.add(candidates[0].path)
            matches.append(ResourceMatch(share_id, status, candidates))
        by_entry[entry["share_id"]] = matches
    return by_entry


def preview_import(repository: ShareImportRepository, data: bytes, assignments: list[str]) -> dict:
    package = preview_share_package(data)
    entries = package.manifest["entries"]
    categories = _tag_categories(repository, entries, assignments)
    default = repository.categories.find_by_system_key("uncategorized")
    matches = _resource_matches(repository, entries)
    return {
        "package_sha256": sha256(data).hexdigest(),
        "manifest": package.manifest,
        "warnings": package.warnings,
        "entries": [
            {
                "share_id": entry["share_id"],
                "status": "conflict" if repository.has_entry(entry["share_id"]) else "new",
                "tag_conflicts": _ratings(entry, categories, default.id if default else None)[1],
                "resources": [item.to_response() for item in matches[entry["share_id"]]],
            }
            for entry in entries
        ],
    }


def _write_resources(
    repository: ShareImportRepository, entry_id: int, matches: list[ResourceMatch], now: datetime,
) -> list[dict]:
    results = []
    for match in matches:
        if match.status == "auto_linked":
            file = match.candidates[0]
            if repository.has_resource(match.share_id):
                match = ResourceMatch(match.share_id, "conflict")
            else:
                try:
                    info = file.path.stat()
                    unchanged = stat.S_ISREG(info.st_mode) and (
                        info.st_size, info.st_mtime_ns
                    ) == (file.size, file.mtime_ns)
                except OSError:
                    unchanged = False
                if unchanged:
                    repository.create_resource(
                        entry_id, match.share_id, path=str(file.path), file_name=file.path.name,
                        extension=file.path.suffix.lower(), size=file.size,
                        mtime_ns=file.mtime_ns, digest=file.digest, now=now,
                    )
                else:
                    match = ResourceMatch(match.share_id, "missing")
        results.append(match.to_response())
    return results


def import_package(
    repository: ShareImportRepository,
    data: bytes,
    preview_sha256: str,
    selected: list[UUID],
    assignments: list[str],
) -> dict:
    if sha256(data).hexdigest() != preview_sha256:
        raise ShareImportConflictError("分享包在预览后发生变化，请重新预览")
    package = preview_share_package(data)
    entries = package.manifest["entries"]
    selected_ids = {str(item) for item in selected}
    if len(selected_ids) != len(selected) or selected_ids - {entry["share_id"] for entry in entries}:
        raise ShareImportSelectionError("所选条目重复或不属于当前分享包")
    selected_entries = [entry for entry in entries if not selected_ids or entry["share_id"] in selected_ids]
    pending = [entry for entry in selected_entries if not repository.has_entry(entry["share_id"])]
    matches = _resource_matches(repository, pending)

    now = datetime.now(timezone.utc)
    imported, skipped = [], []
    with repository.transaction():
        categories = _tag_categories(repository, entries, assignments)
        default = repository.categories.find_by_system_key("uncategorized")
        for entry in selected_entries:
            share_id = entry["share_id"]
            if repository.has_entry(share_id):
                skipped.append(share_id)
                continue
            ratings, conflicts = _ratings(entry, categories, default.id if default else None)
            if conflicts:
                raise ShareImportConflictError("同一条目存在指向同一分类且评分不同的同名标签，请重新选择分类")
            entry_id = repository.create_entry(entry, now)
            for (category_id, _), (name, rating) in ratings.items():
                if category_id is None:
                    if default is None:
                        default = repository.categories.create(
                            name="未分类标签", system_key="uncategorized", now=now,
                        )
                    category_id = default.id
                repository.add_rating(entry_id, category_id, name, rating, now)
            resources = matches.get(share_id)
            if resources is None:
                raise ShareImportConflictError("本地条目状态发生变化，请重新预览")
            imported.append({
                "share_id": share_id,
                "entry_id": entry_id,
                "resources": _write_resources(repository, entry_id, resources, now),
            })
    return {"imported": imported, "skipped_share_ids": skipped, "warnings": package.warnings}
