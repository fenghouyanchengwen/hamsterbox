"""只读分享包预览；不修改数据库，也不将 ZIP 解压到磁盘。"""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import re
import stat
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile
import zlib

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from app.application.share_export import SCHEMA_PATH

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_MANIFEST_BYTES = 10 * 1024 * 1024
MAX_COVER_BYTES = 5 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10001
COVER_NAME = re.compile(r"^covers/[0-9a-f]{64}\.(png|jpg|jpeg|webp)$")


class SharePreviewError(ValueError):
    """分享包无效或不安全；错误不包含本机路径。"""


@dataclass(frozen=True)
class SharePreview:
    manifest: dict
    warnings: tuple[str, ...]


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SharePreviewError("manifest 含有重复字段")
        result[key] = value
    return result


def _check_semantics(manifest):
    entry_ids, resource_ids, tag_names = set(), set(), {}
    for entry in manifest["entries"]:
        if entry["share_id"] in entry_ids:
            raise SharePreviewError("条目分享标识重复")
        entry_ids.add(entry["share_id"])
        refs = set()
        for tag in entry["tags"]:
            ref = tag["tag_ref"]
            if ref in refs or (ref in tag_names and tag_names[ref] != tag["name"]):
                raise SharePreviewError("标签引用重复或定义不一致")
            refs.add(ref)
            tag_names[ref] = tag["name"]
        associated = set()
        for relation in entry["entry_tags"]:
            ref = relation["tag_ref"]
            if ref not in refs or ref in associated:
                raise SharePreviewError("条目标签引用不存在或重复")
            associated.add(ref)
        for resource in entry["resources"]:
            name = resource["file_name"]
            if (name in (".", "..") or any(c in name for c in "/\\:")
                    or any(ord(c) < 32 for c in name)):
                raise SharePreviewError("资源文件名不安全")
            if resource["share_id"] in resource_ids:
                raise SharePreviewError("资源分享标识重复")
            resource_ids.add(resource["share_id"])
            if resource["availability_at_export"] == "present" and (
                resource["sha256"] is None or resource["size_bytes"] is None
            ):
                raise SharePreviewError("可用资源缺少大小或指纹")


def preview_share_package(data: bytes) -> SharePreview:
    """验证包并返回元数据及封面警告；不自动匹配本地文件或执行导入。"""
    if not isinstance(data, bytes) or len(data) > MAX_ARCHIVE_BYTES:
        raise SharePreviewError("分享包内容无效或超过大小限制")
    try:
        with ZipFile(BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise SharePreviewError("分享包文件数量超过限制")
            if sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES:
                raise SharePreviewError("分享包解压后大小超过限制")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or names.count("manifest.json") != 1:
                raise SharePreviewError("manifest 缺失或压缩包路径重复")
            for info in infos:
                if info.filename != "manifest.json" and not COVER_NAME.fullmatch(info.filename):
                    raise SharePreviewError("分享包包含不允许的文件或路径")
                if (info.is_dir() or info.flag_bits & 1 or info.compress_type not in (ZIP_STORED, ZIP_DEFLATED)
                        or (info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16))):
                    raise SharePreviewError("分享包包含不支持的压缩条目")
                limit = MAX_MANIFEST_BYTES if info.filename == "manifest.json" else MAX_COVER_BYTES
                if info.file_size > limit:
                    raise SharePreviewError("分享包内文件超过大小限制")
            raw = archive.read("manifest.json")
            if raw.startswith(b"\xef\xbb\xbf"):
                raise SharePreviewError("manifest 不允许 UTF-8 BOM")
            manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            if list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest)):
                raise SharePreviewError("分享包元数据不符合格式规范")
            _check_semantics(manifest)
            warnings, referenced = [], set()
            for entry in manifest["entries"]:
                cover = entry["cover"]
                if cover is None:
                    continue
                path = cover["archive_path"]
                referenced.add(path)
                if path not in names:
                    warnings.append("条目封面缺失")
                    continue
                try:
                    content = archive.read(path)
                except (BadZipFile, EOFError, zlib.error):
                    warnings.append("条目封面读取失败")
                    continue
                extension = path.rsplit(".", 1)[-1]
                media = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
                signature_ok = (
                    (extension == "png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
                    or (extension in ("jpg", "jpeg") and content.startswith(b"\xff\xd8\xff"))
                    or (extension == "webp" and len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")
                )
                if (len(content) != cover["size_bytes"] or sha256(content).hexdigest() != cover["sha256"]
                        or not path.split("/")[-1].startswith(cover["sha256"] + ".")
                        or cover["media_type"] != media[extension] or not signature_ok):
                    warnings.append("条目封面校验失败")
            if any(name != "manifest.json" and name not in referenced for name in names):
                raise SharePreviewError("分享包含未引用的文件")
            return SharePreview(manifest=manifest, warnings=tuple(warnings))
    except SharePreviewError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError, BadZipFile, RuntimeError,
            NotImplementedError, EOFError, zlib.error, ValueError) as exc:
        raise SharePreviewError("无法读取或校验分享包") from exc
