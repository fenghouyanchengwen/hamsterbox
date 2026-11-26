import json
import importlib.util
import sys
from pathlib import Path
from typing import List
from .interface import FileAdapter


def load_external_plugins(plugins_dir: Path) -> List[FileAdapter]:
    """
    扫描插件目录，动态加载合法的适配器插件。
    """
    adapters: List[FileAdapter] = []

    if not plugins_dir.exists() or not plugins_dir.is_dir():
        return adapters

    for plugin_folder in plugins_dir.iterdir():
        if not plugin_folder.is_dir():
            continue

        manifest_path = plugin_folder / "manifest.json"
        if not manifest_path.exists():
            continue
        #插件文件夹内必须有manifest.json，没有就跳过这个文件夹

        # 1. 读取并解析配置
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            entry_file = plugin_folder / manifest["entry_point"]
            class_name = manifest["adapter_class"]
        except Exception as e:
            print(f"[Plugin] 读取插件配置失败 {plugin_folder.name}: {e}")
            continue

        if not entry_file.exists():
            continue

        # 2. 动态加载模块与异常隔离
        try:
            module_name = f"plugin_{plugin_folder.name}_{entry_file.stem}"
            #根据文件路径创建一个模块规范
            spec = importlib.util.spec_from_file_location(module_name, entry_file)
            if spec is None or spec.loader is None:
                continue

            #根据规范创建一个全新的模块对象
            module = importlib.util.module_from_spec(spec)
            # 临时将插件目录加入 sys.path，防止插件内部互相 import 失败
            sys.path.insert(0, str(plugin_folder))
            spec.loader.exec_module(module)

            # 3. 实例化适配器
            adapter_class = getattr(module, class_name)
            adapter_instance = adapter_class()

            # 简单校验：是否实现了必须的属性
            if hasattr(adapter_instance, "extensions") and hasattr(adapter_instance, "detect_type"):
                adapters.append(adapter_instance)
                print(f"[Plugin] 成功加载插件: {manifest['name']}")
            else:
                print(f"[Plugin] 插件不符合接口规范: {manifest['name']}")

        except Exception as e:
            # 拦截插件加载过程中的任何异常，防止主程序崩溃
            print(f"[Plugin] 加载插件崩溃 {plugin_folder.name}: {e}")
        finally:
            # 加载完毕，从 sys.path 移除，保持环境干净
            if str(plugin_folder) in sys.path:
                sys.path.remove(str(plugin_folder))

    return adapters
