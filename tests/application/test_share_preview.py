from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from app.application.share_preview import SharePreviewError, preview_share_package
from app.application.share_export import export_share_package
from app.db.share_export_repository import ExportEntry


@pytest.fixture
def manifest():
    path = Path(__file__).resolve().parents[2] / "docs/examples/share-package-v1/single-entry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def package(manifest, extras=(), raw=None, compression=ZIP_DEFLATED):
    output = BytesIO()
    with ZipFile(output, "w", compression=compression) as archive:
        archive.writestr("manifest.json", raw if raw is not None else json.dumps(manifest, ensure_ascii=False))
        for name, content in extras:
            archive.writestr(name, content)
    return output.getvalue()


def test_valid_package_preview_is_read_only(manifest):
    before = deepcopy(manifest)
    preview = preview_share_package(package(manifest))
    assert preview.manifest == before
    assert preview.warnings == ()
    assert manifest == before


def test_preview_accepts_actual_exporter_output():
    now = datetime.now(timezone.utc)
    entry = ExportEntry(str(uuid4()), "示例条目", "book", None, "评价", now, now, (), ())

    class Repository:
        def get(self, entry_id):
            return entry if entry_id == 1 else None

    preview = preview_share_package(export_share_package(Repository(), [1], str(uuid4())))
    assert preview.manifest["entries"][0]["share_id"] == entry.share_id
    assert preview.manifest["entries"][0]["source_review"] == "评价"


@pytest.mark.parametrize("value", [b"not-a-zip", b"", b"PK\x03\x04broken"])
def test_bad_archive_rejected(value):
    with pytest.raises(SharePreviewError):
        preview_share_package(value)


@pytest.mark.parametrize("path", ["../evil.txt", "/tmp/evil", "covers/../x.png", "folder\\evil", "original.exe"])
def test_unsafe_or_unexpected_archive_paths_rejected(manifest, path):
    with pytest.raises(SharePreviewError):
        preview_share_package(package(manifest, [(path, b"unsafe")]))


def test_duplicate_manifest_rejected(manifest):
    with pytest.warns(UserWarning):
        data = package(manifest, [("manifest.json", b"{}")])
    with pytest.raises(SharePreviewError, match="重复"):
        preview_share_package(data)


def test_duplicate_json_keys_rejected(manifest):
    with pytest.raises(SharePreviewError, match="重复字段"):
        preview_share_package(package(manifest, raw=b'{"format":"a","format":"b"}'))


def test_utf8_bom_rejected(manifest):
    with pytest.raises(SharePreviewError, match="BOM"):
        preview_share_package(package(manifest, raw=b"\xef\xbb\xbf{}"))


def test_unknown_version_and_invalid_rating_rejected(manifest):
    manifest["format_version"] = "2.0.0"
    with pytest.raises(SharePreviewError, match="格式规范"):
        preview_share_package(package(manifest))
    manifest["format_version"] = "1.0.0"
    manifest["entries"][0]["entry_tags"][0]["rating"] = 11
    with pytest.raises(SharePreviewError, match="格式规范"):
        preview_share_package(package(manifest))


def test_broken_tag_reference_rejected(manifest):
    manifest["entries"][0]["entry_tags"][0]["tag_ref"] = str(uuid4())
    with pytest.raises(SharePreviewError, match="引用"):
        preview_share_package(package(manifest))


def test_duplicate_entry_rejected(manifest):
    manifest["entries"].append(deepcopy(manifest["entries"][0]))
    with pytest.raises(SharePreviewError, match="条目分享标识重复"):
        preview_share_package(package(manifest))


@pytest.mark.parametrize("name", ["../game.exe", "C:\\secret.exe", "/tmp/a", ".", "bad\nname"])
def test_unsafe_resource_names_rejected(manifest, name):
    manifest["entries"][0]["resources"][0]["file_name"] = name
    with pytest.raises(SharePreviewError, match="文件名"):
        preview_share_package(package(manifest))


def test_present_resource_requires_fingerprint(manifest):
    manifest["entries"][0]["resources"][0]["sha256"] = None
    with pytest.raises(SharePreviewError, match="指纹"):
        preview_share_package(package(manifest))


def test_cover_integrity_and_missing_cover_warning(manifest):
    content = b"\x89PNG\r\n\x1a\n" + b"illustrative contents"
    digest = sha256(content).hexdigest()
    path = f"covers/{digest}.png"
    manifest["entries"][0]["cover"] = {"archive_path": path, "media_type": "image/png", "sha256": digest, "size_bytes": len(content)}
    assert preview_share_package(package(manifest, [(path, content)])).warnings == ()
    assert preview_share_package(package(manifest)).warnings == ("条目封面缺失",)
    assert preview_share_package(package(manifest, [(path, content + b"changed")])).warnings == ("条目封面校验失败",)


def test_unreferenced_cover_rejected(manifest):
    path = "covers/" + "a" * 64 + ".png"
    with pytest.raises(SharePreviewError, match="未引用"):
        preview_share_package(package(manifest, [(path, b"content")]))


def test_symlink_and_unsupported_compression_rejected(manifest):
    info = ZipInfo("covers/" + "a" * 64 + ".png")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with pytest.raises(SharePreviewError, match="不支持"):
        preview_share_package(package(manifest, [(info, b"link")]))
    with pytest.raises(SharePreviewError, match="不支持"):
        preview_share_package(package(manifest, compression=ZIP_BZIP2))


def test_size_limit_checked_before_read(manifest, monkeypatch):
    monkeypatch.setattr("app.application.share_preview.MAX_ARCHIVE_BYTES", 16)
    with pytest.raises(SharePreviewError, match="大小限制"):
        preview_share_package(package(manifest))
