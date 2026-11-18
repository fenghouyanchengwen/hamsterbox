"""分享包导出原型：只生成元数据包，不修改资料库或原始文件。"""

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
import stat
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from jsonschema import Draft202012Validator, FormatChecker

from app.application.errors import CodedApplicationError
from app.db.share_export_repository import ExportResource, ShareExportRepository
from app.domain.share_package_schema import SHARE_PACKAGE_V1_SCHEMA

MAX_MANIFEST_BYTES = 10 * 1024 * 1024
VALIDATOR = Draft202012Validator(SHARE_PACKAGE_V1_SCHEMA, format_checker=FormatChecker())


class ShareExportError(CodedApplicationError, ValueError):
    """不泄露本机路径的导出错误。"""

    code = "SHARE_EXPORT_INVALID"
    status_code = 422


def _utc(value: datetime) -> str:
    # SQLite 将团队约定的 UTC 时间以无时区形式存储。
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _resource_snapshot(resource: ExportResource) -> dict:
    name = resource.file_name
    if (not name or name in (".", "..") or any(c in name for c in "/\\:")
            or any(ord(c) < 32 for c in name)):
        raise ShareExportError("资源文件名不安全")
    try:
        fd = os.open(resource.path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ShareExportError("资源不是普通文件")
            digest = sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ShareExportError("计算资源指纹时文件发生变化，请重试")
        size, fingerprint, availability = after.st_size, digest.hexdigest(), "present"
    except FileNotFoundError:
        size, fingerprint, availability = resource.size_bytes, resource.sha256, "missing"
    except OSError as exc:
        raise ShareExportError("无法读取资源文件") from exc
    return {
        "share_id": resource.share_id, "file_name": name,
        "extension": resource.extension, "size_bytes": size,
        "sha256": fingerprint, "availability_at_export": availability,
    }


def snapshot_share_entries(repository: ShareExportRepository, entry_ids: list[int]) -> list[dict]:
    if not entry_ids or any(type(item) is not int or item <= 0 for item in entry_ids):
        raise ShareExportError("请选择至少一个有效条目")
    if len(set(entry_ids)) != len(entry_ids):
        raise ShareExportError("所选条目不能重复")

    snapshots = [repository.get(entry_id) for entry_id in entry_ids]
    if any(entry is None for entry in snapshots):
        raise ShareExportError("所选条目不存在或不是正式条目")
    refs = {}
    entries = []
    for entry in snapshots:
        tags, relationships = [], []
        for tag in entry.tags:
            if tag.local_id not in refs:
                refs[tag.local_id] = str(uuid4())
            ref = refs[tag.local_id]
            tags.append({"tag_ref": ref, "name": tag.name})
            relationships.append({"tag_ref": ref, "rating": tag.rating})
        entries.append({
            "share_id": entry.share_id, "title": entry.title, "type": entry.type,
            "description": entry.description, "review_mode": "original",
            "source_review": entry.review, "share_review": None,
            "created_at": _utc(entry.created_at), "updated_at": _utc(entry.updated_at),
            "resources": [_resource_snapshot(resource) for resource in entry.resources],
            "tags": tags, "entry_tags": relationships, "cover": None,
        })
    return entries


def create_share_manifest(entries: list[dict], source_library_id: str, app_version: str) -> dict:
    try:
        library_id = str(UUID(source_library_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ShareExportError("来源资料库标识必须是有效 UUID") from exc

    return {
        "format": "hamsterbox-share-package",
        "format_version": "1.0.0",
        "generated_by": {"name": "HamsterBox", "version": app_version},
        "package_id": str(uuid4()),
        "source_library_id": library_id,
        "created_at": _utc(datetime.now(timezone.utc)),
        "entries": entries,
    }


def encode_share_manifest(manifest: dict) -> bytes:
    if not VALIDATOR.is_valid(manifest):
        raise ShareExportError("分享包元数据不符合格式规范")
    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ShareExportError("分享包元数据超过大小限制")
    return encoded


def pack_share_manifest(manifest: dict) -> bytes:
    encoded = encode_share_manifest(manifest)
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", encoded)
    return output.getvalue()


def export_share_package(repository: ShareExportRepository, entry_ids: list[int],
                         source_library_id: str | None = None, app_version: str = "0.3.0") -> bytes:
    entries = snapshot_share_entries(repository, entry_ids)
    library_id = source_library_id if source_library_id is not None else repository.get_or_create_library_id()
    return pack_share_manifest(create_share_manifest(entries, library_id, app_version))
