from pathlib import Path
from ..enums import EntryType

class EbookAdapter:
    extensions = (".epub", ".pdf", ".mobi")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.BOOK

    def read_metadata(self, path: Path,) -> dict[str, object]:
        meta: dict[str, object] = {"file_size": path.stat().st_size if path.exists() else 0,"parse_status": "success"}
        # 与image适配器相同
        # parse_status默认成功，遇到异常会改为 "failed"
        suffix = path.suffix.lower()
        try:
            if suffix == ".epub":
                self._read_epub(path, meta)
            elif suffix == ".pdf":
                self._read_pdf(path, meta)
            elif suffix == ".mobi":
                self._read_mobi(path, meta)
        except Exception as exc:
            # 统一捕获底层解析异常（如文件损坏、非标准格式）
            meta["parse_status"] = "failed"
            meta["parse_error"] = str(exc)

        return meta
        '''
        if suffix == ".epub":
            try:
                from ebooklib import epub
                book = epub.read_epub(str(path))
                titles = book.get_metadata("DC", "title")
                creators = book.get_metadata("DC", "creator")
                #book.get_metadata返回的是一个列表
                if titles:
                    meta["title"] = titles[0][0]
                if creators:
                    meta["author"] = creators[0][0]
                #取数组的[0][0]拿到文本
            except Exception:
                pass
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                info = reader.metadata
                if info:
                    if reader.metadata.title:
                        meta["title"] = reader.metadata.title
                    if reader.metadata.author:
                        meta["author"] = reader.metadata.author
                meta["pages"] = len(reader.pages)
            except Exception:
                pass
        return meta
        '''

    def _read_epub(self, path: Path, meta: dict):
        from ebooklib import epub
        book = epub.read_epub(str(path))

        # 提取标题和作者
        titles = book.get_metadata("DC", "title")
        creators = book.get_metadata("DC", "creator")
        # book.get_metadata返回的是一个列表
        # 因此取数组的[0][0]拿到文本
        if titles:
            meta["title"] = str(titles[0][0])
        if creators:
            meta["author"] = str(creators[0][0])

        # 尝试读取页数
        try:
            if hasattr(book, 'pages') and book.pages:
                meta["pages"] = len(book.pages)
        except Exception:
            # 如果文件没有内嵌分页标记，get_pages 会失败或返回空
            # 这属于正常现象（无页数），不标记为解析失败
            pass

    def _read_pdf(self, path: Path, meta: dict):
        from pypdf import PdfReader
        reader = PdfReader(str(path))

        # 提取标题和作者
        info = reader.metadata
        if info:
            if info.title:
                meta["title"] = info.title
            if info.author:
                meta["author"] = info.author

        # 提取页数
        meta["pages"] = len(reader.pages)

    def _read_mobi(self, path: Path, meta: dict):
        from ebookatty import MetadataFetcher
        # 实例化元数据提取器
        fetcher = MetadataFetcher()
        metadata = fetcher.extract_metadata(str(path))

        if metadata:
            if metadata.get("title"):
                meta["title"] = metadata.get("title")
            author = metadata.get("author") or metadata.get("creator")
            # ebookatty 返回的字段名是 'author'，但有时也可能叫 'creator'
            if author:
                meta["author"] = author
            meta["metadata_extracted"] = True
        else:
            # 文件解析成功，但内部没有元数据块（属于正常现象）
            meta["metadata_extracted"] = False

    def supports_preview(self) -> bool:
        return False
