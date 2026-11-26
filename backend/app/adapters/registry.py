from pathlib import Path
from .interface import FileAdapter
from .enums import EntryType

class TypeRegistry:
    def __init__(self) -> None:
        self._by_extension: dict[str, FileAdapter] = {}
        #查询主索引：key：小写、没有前缀点；value：适配器实例
        self._adapters: list[FileAdapter] = []
        #保存所有已注册适配器的列表
        self._default_adapter: FileAdapter | None = None
        # 全局兜底适配器，当后缀查不到时使用

    def register(self, adapter: FileAdapter, is_default: bool = False) -> None:
        # 如果是全局兜底适配器，用来适配所有OTHER类型
        if is_default:
            if self._default_adapter is not None:
                raise ValueError("全局兜底适配器已存在，不能重复注册")
            self._default_adapter = adapter
            self._adapters.append(adapter)
            return

        if not adapter.extensions:
            raise ValueError(f"适配器未声明扩展名: {type(adapter).__name__}")

        if any(type(a) is type(adapter) for a in self._adapters):
            raise ValueError(f"适配器重复注册: {type(adapter).__name__}")

        normalized_exts = [ext.lower().lstrip(".") for ext in adapter.extensions]
        for normalized in normalized_exts:
            if not normalized:
                raise ValueError(
                    f"适配器声明了空扩展名: {type(adapter).__name__}"
                )
            if normalized in self._by_extension:
                existing = self._by_extension[normalized]
                raise ValueError(
                    f"扩展名冲突: .{normalized}，"
                    f"已被 {type(existing).__name__} 占用"
                )

        self._adapters.append(adapter)
        for normalized in normalized_exts:
            self._by_extension[normalized] = adapter


    def for_extension(self, extension: str) -> FileAdapter | None:
        normalized = extension.lower().lstrip(".")#统一输入，删除“.”并全部转为小写
        adapter = self._by_extension.get(normalized)
        #如果字典里查不到，就返回全局兜底
        if adapter is not None:
            return adapter
        return self._default_adapter

    def detect(self, path: Path) -> EntryType:
        adapter = self.for_extension(path.suffix)#path.suffix取后缀名，然后调用for_extension统一格式
        if adapter is None:
            return EntryType.OTHER
        return adapter.detect_type(path)

    def adapters(self) -> tuple[FileAdapter, ...]:
        """返回所有已注册适配器的只读快照"""
        return tuple(self._adapters)

    def supported_extensions(self) -> tuple[str, ...]:
        """返回所有已注册扩展名的只读快照（归一化后的格式）"""
        return tuple(self._by_extension.keys())
