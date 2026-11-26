from pathlib import Path
from ..enums import EntryType

class FallbackAdapter:
    """
        兜底/占位适配器。
        用于处理无专门解析逻辑的文件类型（如 .exe, .txt, .glb 等），仅提供基础信息。
    """
    def __init__(self, entry_type: EntryType, extensions: tuple[str, ...]= ()):
        self._entry_type = entry_type
        self.extensions = extensions

    def detect_type(self, path: Path) -> EntryType:
        return self._entry_type

    def read_metadata(self, path: Path) -> dict[str, object]:
        file_size = 0
        try:
            if path.exists() and path.is_file():
                file_size = path.stat().st_size
        except OSError:
            # 捕获权限不足或文件被锁定等底层异常，安全兜底
            pass

        return {"file_size": file_size}

    def supports_preview(self) -> bool:
        return False
