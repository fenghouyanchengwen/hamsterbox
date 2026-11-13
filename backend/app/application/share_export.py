"""分享包导出原型：只生成元数据包，不修改资料库或原始文件。"""

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import stat
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from app.db.share_export_repository import ShareExportRepository

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "share-package-v1.schema.json"
MAX_MANIFEST_BYTES = 10 * 1024 * 1024


class ShareExportError(ValueError):
    """不泄露本机路径的导出错误。"""


def _utc(value: datetime) -> str:
    # SQLite 将团队约定的 UTC 时间以无时区形式存储。
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _resource_snapshot(resource) -> dict:
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
        size, fingerprint, availability = None, None, "missing"
    except OSError as exc:
        raise ShareExportError("无法读取资源文件") from exc
    return {
        "share_id": resource.share_id, "file_name": name,
        "extension": resource.extension, "size_bytes": size,
        "sha256": fingerprint, "availability_at_export": availability,
    }


def export_share_package(repository: ShareExportRepository, entry_ids: list[int],
                         source_library_id: str, app_version: str = "0.1.0") -> bytes:
    """返回 ZIP 格式的 .hbox 字节；调用者负责安全保存。

    本原型仅支持完整正式条目、原评价和全部关联标签；来源资料库 UUID 必须由
    调用方提供，不能随机伪造稳定标识。封面、部分资源分享和 HTTP 接口待联调。
    """
    if not entry_ids or any(type(item) is not int or item <= 0 for item in entry_ids):
        raise ShareExportError("请选择至少一个有效条目")
    if len(set(entry_ids)) != len(entry_ids):
        raise ShareExportError("所选条目不能重复")
    try:
        library_id = str(UUID(source_library_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ShareExportError("来源资料库标识必须是有效 UUID") from exc

    snapshots = [repository.get(entry_id) for entry_id in entry_ids]
    if any(entry is None for entry in snapshots):
        raise ShareExportError("所选条目不存在或不是正式条目")
    refs = {}
    entries = []
    for entry in snapshots:
        tags, relationships = [], []
        for tag in entry.tags:
            ref = refs.setdefault(tag.local_id, str(uuid4()))
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
    manifest = {
        "format": "hamsterbox-share-package", "format_version": "1.0.0",
        "generated_by": {"name": "HamsterBox", "version": app_version},
        "package_id": str(uuid4()), "source_library_id": library_id,
        "created_at": _utc(datetime.now(timezone.utc)), "entries": entries,
    }
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest))
    except (OSError, ValueError, SchemaError) as exc:
        raise ShareExportError("无法读取或解析分享包格式规范") from exc
    if errors:
        raise ShareExportError("分享包元数据不符合格式规范")
    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ShareExportError("分享包元数据超过大小限制")
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", encoded)
    return output.getvalue()
