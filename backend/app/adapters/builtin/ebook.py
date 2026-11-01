from pathlib import Path
from ..enums import EntryType

class EbookAdapter:
    extensions = (".epub", ".pdf", ".mobi")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.BOOK

    def read_metadata(self, path: Path) -> dict[str, object]:
        meta: dict[str, object] = {"file_size": path.stat().st_size if path.exists() else 0}
        suffix = path.suffix.lower()
        if suffix == ".epub":
            try:
                import ebooklib
                book = epub.read_epub(str(path))
                titles = book.get_metadata("DC", "title")
                creators = book.get_metadata("DC", "creator")
                if titles:
                    meta["title"] = titles[0][0]
                if creators:
                    meta["author"] = creators[0][0]
            except Exception:
                pass
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                info = reader.metadata
                if info:
                    meta["title"] = info.title
                    meta["author"] = info.author
            except Exception:
                pass
        return meta

    def supports_preview(self) -> bool:
        return False
