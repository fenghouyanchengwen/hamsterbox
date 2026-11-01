from pathlib import Path
from ..enums import EntryType

class ImageAdapter:
    extensions = (".png", ".jpg", ".jpeg", ".webp")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.IMAGE

    def read_metadata(self, path: Path) -> dict[str, object]:
        try:
            with Image.open(path) as img:
                width, height = img.size
            return {"width": width, "height": height, "file_size": path.stat().st_size}
        except Exception:
            return {"file_size": path.stat().st_size if path.exists() else 0}

    def supports_preview(self) -> bool:
        return True
