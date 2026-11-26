# tests/adapters/test_plugin_loader.py
import json
import zipfile
import pytest
from pathlib import Path

from app.adapters.plugin_loader import load_external_plugins
from app.adapters.bootstrap import build_registry
from app.adapters.enums import EntryType


@pytest.fixture
def temp_plugin_env(tmp_path: Path):
    """准备一个临时插件环境和测试文件"""
    # 1. 创建插件目录结构
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    archive_plugin = plugin_dir / "archive_support"
    archive_plugin.mkdir()

    # 2. 写入 manifest.json
    manifest_content = {
        "name": "Archive Support",
        "version": "1.0.0",
        "entry_point": "archive_adapter.py",
        "adapter_class": "ArchiveAdapter"
    }
    (archive_plugin / "manifest.json").write_text(
        json.dumps(manifest_content), encoding="utf-8"
    )

    # 3. 写入插件代码（这里直接复制你的插件代码，确保测试不依赖外部文件）
    plugin_code = """
import zipfile
import tarfile
from pathlib import Path
from app.adapters.enums import EntryType

class ArchiveAdapter:
    extensions = (".zip", ".rar", ".7z", ".tar", ".gz")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.OTHER

    def read_metadata(self, path: Path) -> dict[str, object]:
        meta = {"file_size": path.stat().st_size if path.exists() else 0, "is_archive": True}
        suffix = path.suffix.lower()
        try:
            if suffix == ".zip":
                with zipfile.ZipFile(path, 'r') as z:
                    meta["file_count"] = len(z.namelist())
                    meta["archive_format"] = "ZIP"
        except Exception:
            meta["parse_status"] = "failed"
        return meta

    def supports_preview(self) -> bool:
        return False
"""
    (archive_plugin / "archive_adapter.py").write_text(plugin_code, encoding="utf-8")

    return tmp_path / "plugins"


def test_load_external_plugin(temp_plugin_env):
    """测试1：能否成功从外部目录加载插件"""
    adapters = load_external_plugins(temp_plugin_env)
    assert len(adapters) == 1
    assert ".zip" in adapters[0].extensions
    assert type(adapters[0]).__name__ == "ArchiveAdapter"


def test_registry_integration(temp_plugin_env):
    """测试2：插件注册后，注册表能否正确把 .zip 路由给该插件"""
    registry = build_registry(plugins_dir=temp_plugin_env)
    adapter = registry.for_extension(".zip")

    # 验证拿到的是我们注册的外部插件
    assert adapter is not None
    assert type(adapter).__name__ == "ArchiveAdapter"

    # 验证类型识别
    assert registry.detect(Path("test.zip")) == EntryType.OTHER


def test_plugin_metadata_valid_zip(temp_plugin_env, tmp_path):
    """测试3：解析合法的 ZIP 文件，验证文件数量"""
    # 动态生成一个包含 3 个文件的合法 ZIP
    test_zip = tmp_path / "valid.zip"
    with zipfile.ZipFile(test_zip, 'w') as z:
        z.writestr("file1.txt", "content")
        z.writestr("file2.txt", "content")
        z.writestr("file3.txt", "content")

    adapters = load_external_plugins(temp_plugin_env)
    meta = adapters[0].read_metadata(test_zip)

    assert meta["is_archive"] is True
    assert meta["archive_format"] == "ZIP"
    assert meta["file_count"] == 3


def test_plugin_metadata_corrupt_zip(temp_plugin_env, tmp_path):
    """测试4：解析损坏的 ZIP 文件，验证异常隔离与安全兜底"""
    # 创建一个假的 ZIP 文件（写入纯文本）
    bad_zip = tmp_path / "fake.zip"
    bad_zip.write_text("this is not a real zip file")

    adapters = load_external_plugins(temp_plugin_env)
    meta = adapters[0].read_metadata(bad_zip)

    # 断言：插件内部捕获了异常，没有崩溃，且返回了失败的标记
    assert meta["is_archive"] is True
    assert meta["parse_status"] == "failed"
