from pathlib import Path
from .registry import TypeRegistry
from .enums import EntryType
from .builtin.image import ImageAdapter
from .builtin.video import VideoAdapter
from .builtin.ebook import EbookAdapter
from .builtin.fallback import FallbackAdapter

from .plugin_loader import load_external_plugins
##

def build_registry(plugins_dir: Path | None = None) -> TypeRegistry:
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

    # 其他文件
    registry.register(FallbackAdapter(EntryType.OTHER), is_default=True)

    if plugins_dir is not None:
        # 1. 扫描插件目录，获取外部插件实例列表
        external_adapters = load_external_plugins(plugins_dir)

        for adapter in external_adapters:
            try:
                # 2. 尝试注册到注册表
                # registry.register 内部已经实现了重名和扩展名冲突检测
                registry.register(adapter)
            except ValueError as e:
                # 3. 核心防崩溃：如果插件注册冲突（如扩展名被内置适配器占用）
                # 绝不能抛出异常导致主程序启动失败，只打印警告并跳过该插件
                print(f"[Plugin Warning] 插件被拒绝加载: {e}")
            except Exception as e:
                print(f"[Plugin Error] 插件注册时发生未知错误: {e}")

    return registry
