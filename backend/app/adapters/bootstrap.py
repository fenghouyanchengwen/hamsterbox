from .registry import TypeRegistry
from .enums import EntryType
from .builtin.image import ImageAdapter
from .builtin.video import VideoAdapter
from .builtin.ebook import EbookAdapter
from .builtin.fallback import FallbackAdapter


def build_registry() -> TypeRegistry:
    """
    构建并返回一个包含所有内置适配器的类型注册表。
    在应用启动时（如 FastAPI 的 lifespan）调用此函数。
    """
    registry = TypeRegistry()

    # 1. 注册三大核心真实适配器
    registry.register(ImageAdapter())
    registry.register(VideoAdapter())
    registry.register(EbookAdapter())

    # 2. 注册占位/兜底适配器
    # 游戏/可执行文件
    registry.register(FallbackAdapter(EntryType.GAME, extensions=(".exe", ".lnk")))

    # 3D 模型
    registry.register(FallbackAdapter(EntryType.MODEL, extensions=(".glb", ".gltf", ".obj")))

    # 文本文件 (因为数据库不支持 text，所以归入 OTHER)
    registry.register(FallbackAdapter(EntryType.OTHER), is_default=True)

    return registry
