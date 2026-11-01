from pathlib import Path
import pytest

# 如果你改成了 enums.py
from app.adapters.enums import EntryType
from app.adapters.registry import TypeRegistry


# ==========================================
# 1. 测试用的 Mock 适配器
# ==========================================
class MockImageAdapter:
    extensions = (".jpg", ".jpeg", ".png")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.IMAGE

    def read_metadata(self, path: Path) -> dict[str, object]:
        return {}

    def supports_preview(self) -> bool:
        return True


class MockVideoAdapter:
    extensions = (".mp4", ".mkv")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.VIDEO

    def read_metadata(self, path: Path) -> dict[str, object]:
        return {}

    def supports_preview(self) -> bool:
        return False


# ==========================================
# 2. Pytest Fixtures (提供干净的测试环境)
# ==========================================
@pytest.fixture
def registry() -> TypeRegistry:
    """每个测试用例都提供一个全新的、空白的注册表"""
    return TypeRegistry()


@pytest.fixture
def populated_registry(registry: TypeRegistry) -> TypeRegistry:
    """提供一个已经注册了图片和视频适配器的注册表"""
    registry.register(MockImageAdapter())
    registry.register(MockVideoAdapter())
    return registry


# ==========================================
# 3. 测试扩展名查询 (for_extension)
# ==========================================
def test_for_extension_normalization(populated_registry: TypeRegistry):
    """测试大小写混合、有无点号的情况都能正确查询到适配器"""
    assert isinstance(populated_registry.for_extension(".jpg"), MockImageAdapter)
    assert isinstance(populated_registry.for_extension("jpg"), MockImageAdapter)
    assert isinstance(populated_registry.for_extension(".JPG"), MockImageAdapter)
    assert isinstance(populated_registry.for_extension("JpG"), MockImageAdapter)

    assert isinstance(populated_registry.for_extension(".MP4"), MockVideoAdapter)


def test_for_extension_unknown(populated_registry: TypeRegistry):
    """测试未注册的扩展名返回 None"""
    assert populated_registry.for_extension(".xyz") is None
    assert populated_registry.for_extension("unknown") is None


# ==========================================
# 4. 测试类型识别 (detect)
# ==========================================
@pytest.mark.parametrize("filename, expected_type", [
    ("photo.jpg", EntryType.IMAGE),
    ("video.MKV", EntryType.VIDEO),  # 测试大写后缀
    ("book.final.epub", EntryType.OTHER),  # 测试多点文件，.epub 未注册，应走兜底
    ("unknown.xyz", EntryType.OTHER),  # 测试未知后缀
    ("README", EntryType.OTHER),  # 测试无后缀
    ("archive.tar.gz", EntryType.OTHER),  # 测试多段后缀，按 .gz 识别，返回 OTHER
])
def test_detect_type(populated_registry: TypeRegistry, tmp_path: Path, filename: str, expected_type: EntryType):
    """测试通过路径识别类型，并确保未知类型稳定兜底为 OTHER"""
    # 在临时目录中创建一个空文件用于测试
    file_path = tmp_path / filename
    file_path.touch()

    assert populated_registry.detect(file_path) == expected_type


# ==========================================
# 5. 测试异常拦截与注册原子性
# ==========================================
def test_register_empty_extensions(registry: TypeRegistry):
    """测试：拒绝没有声明扩展名的适配器"""

    class EmptyAdapter:
        extensions = ()

        def detect_type(self, path): ...

        def read_metadata(self, path): ...

        def supports_preview(self): ...

    with pytest.raises(ValueError, match="未声明扩展名"):
        registry.register(EmptyAdapter())


def test_register_duplicate_adapter(registry: TypeRegistry):
    """测试：拒绝重复注册同一类适配器"""
    registry.register(MockImageAdapter())

    with pytest.raises(ValueError, match="适配器重复注册"):
        registry.register(MockImageAdapter())


def test_register_extension_conflict(populated_registry: TypeRegistry):
    """测试：拒绝扩展名冲突"""

    class ConflictingAdapter:
        extensions = (".mp4",)  # 与 MockVideoAdapter 冲突

        def detect_type(self, path): ...

        def read_metadata(self, path): ...

        def supports_preview(self): ...

    with pytest.raises(ValueError, match="扩展名冲突: .mp4"):
        populated_registry.register(ConflictingAdapter())


def test_register_atomicity_on_conflict(registry: TypeRegistry):
    """
    测试：注册时发生冲突必须原子回滚。
    如果适配器声明了 (".new", ".jpg")，但 .jpg 已存在，则 .new 也不能被注册成功。
    """
    registry.register(MockImageAdapter())  # 占用 .jpg

    class MultiAdapter:
        extensions = (".new", ".jpg")  # .new 可用，.jpg 冲突

        def detect_type(self, path): ...

        def read_metadata(self, path): ...

        def supports_preview(self): ...

    with pytest.raises(ValueError, match="扩展名冲突: .jpg"):
        registry.register(MultiAdapter())

    # 验证原子性：.new 绝对不能进入注册表
    assert registry.for_extension(".new") is None
    # 验证账本没有错误增加
    assert len(registry.adapters()) == 1


# ==========================================
# 6. 测试只读快照接口
# ==========================================
def test_readonly_snapshots(populated_registry: TypeRegistry):
    """测试提供的 adapters() 和 supported_extensions() 是不可变的元组"""
    adapters = populated_registry.adapters()
    assert isinstance(adapters, tuple)
    assert len(adapters) == 2

    extensions = populated_registry.supported_extensions()
    assert isinstance(extensions, tuple)
    assert "jpg" in extensions
    assert ".jpg" not in extensions  # 确保暴露的是归一化后的扩展名
