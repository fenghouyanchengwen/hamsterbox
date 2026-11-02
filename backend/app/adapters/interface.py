from pathlib import Path
from typing import Protocol
from .enums import EntryType

class FileAdapter(Protocol):
    extensions: tuple[str, ...]

    def detect_type(self, path: Path) -> EntryType: ...
    def read_metadata(self, path: Path) -> dict[str, object]: ...
    def supports_preview(self) -> bool: ...
