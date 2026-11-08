import pytest
from pathlib import Path
from PIL import Image

from app.adapters.enums import EntryType
from app.adapters.builtin.image import ImageAdapter
from app.adapters.builtin.ebook import EbookAdapter
from app.adapters.builtin.fallback import FallbackAdapter
from app.adapters.registry import TypeRegistry


# ==========================================
# 1. 测试图片适配器 (ImageAdapter)
# ==========================================
def test_image_adapter_success(tmp_path: Path):
    """测试正常图片读取：生成一张 100x50 的红图"""
    img_path = tmp_path / "test.jpg"
    # 用代码动态生成一张真实图片
    img = Image.new("RGB", (100, 50), color="red")
    img.save(img_path)

    adapter = ImageAdapter()
    assert adapter.detect_type(img_path) == EntryType.IMAGE
    assert adapter.supports_preview() is True

    meta = adapter.read_metadata(img_path)
    assert meta["width"] == 100
    assert meta["height"] == 50
    assert meta["file_size"] > 0
    assert meta["format"] == "JPEG"


def test_image_adapter_corrupt_file(tmp_path: Path):
    """测试坏图片兜底：伪造一个 .png 后缀的文本文件"""
    fake_img = tmp_path / "fake.png"
    fake_img.write_text("not an image")

    adapter = ImageAdapter()
    meta = adapter.read_metadata(fake_img)

    # 解析失败不应该抛异常，只应该返回 file_size
    assert "width" not in meta
    assert meta["file_size"] > 0


# ==========================================
# 2. 测试电子书适配器 (EbookAdapter)
# ==========================================
def test_ebook_adapter_parse_failed(tmp_path: Path):
    """测试电子书解析失败：伪造损坏的 epub 文件，验证 parse_status"""
    fake_epub = tmp_path / "broken.epub"
    fake_epub.write_text("Invalid epub content")

    adapter = EbookAdapter()
    meta = adapter.read_metadata(fake_epub)

    assert meta["parse_status"] == "failed"
    assert "parse_error" in meta


# ==========================================
# 3. 测试全局兜底机制 (Fallback & Registry)
# ==========================================
def test_registry_global_fallback():
    """测试注册表全局兜底：未知后缀应返回 OTHER 且能正常读取"""
    registry = TypeRegistry()

    # 注册全局兜底
    fallback_adapter = FallbackAdapter(EntryType.OTHER)
    registry.register(fallback_adapter, is_default=True)

    # 创建一个完全未知的后缀文件
    dummy_path = Path("some_unknown_file.xyz")

    # 查找适配器，应该能拿到全局兜底的 FallbackAdapter
    adapter = registry.for_extension(dummy_path.suffix)
    assert adapter is not None
    assert isinstance(adapter, FallbackAdapter)

    # 识别类型应该为 OTHER
    assert registry.detect(dummy_path) == EntryType.OTHER
