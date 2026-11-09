"""Alpha 2 smoke tests for built-in image, video, and ebook adapters."""

from pathlib import Path
from types import SimpleNamespace

from ebooklib import epub
from pypdf import PdfWriter
import pytest

from app.adapters.bootstrap import build_registry
from app.adapters.builtin.ebook import EbookAdapter
from app.adapters.builtin.video import VideoAdapter
from app.adapters.enums import EntryType


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known defect: build_registry registers multiple FallbackAdapter "
        "instances, but TypeRegistry rejects duplicate adapter classes."
    ),
)
def test_built_in_registry_routes_alpha2_file_types() -> None:
    registry = build_registry()

    assert registry.detect(Path("cover.PNG")) == EntryType.IMAGE
    assert registry.detect(Path("trailer.MP4")) == EntryType.VIDEO
    assert registry.detect(Path("manual.PDF")) == EntryType.BOOK


def test_video_adapter_extracts_track_metadata_without_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video fixture")
    tracks = [
        SimpleNamespace(track_type="General", format="MPEG-4"),
        SimpleNamespace(
            track_type="Video",
            duration=12_500,
            width=640,
            height=360,
            codec_id="AVC",
        ),
    ]
    monkeypatch.setattr(
        "app.adapters.builtin.video.MediaInfo.parse",
        lambda _path: SimpleNamespace(tracks=tracks),
    )

    adapter = VideoAdapter()
    metadata = adapter.read_metadata(video_path)

    assert adapter.detect_type(video_path) == EntryType.VIDEO
    assert metadata["duration_ms"] == 12_500
    assert metadata["width"] == 640
    assert metadata["height"] == 360
    assert metadata["codec"] == "AVC"
    assert metadata["format"] == "MPEG-4"
    assert adapter.supports_preview() is False


def test_ebook_adapter_reads_epub_and_pdf_metadata(tmp_path: Path) -> None:
    epub_path = tmp_path / "sample.epub"
    book = epub.EpubBook()
    book.set_identifier("alpha2-epub-fixture")
    book.set_title("Alpha EPUB")
    book.add_author("QA Author")
    book.set_language("en")
    chapter = epub.EpubHtml(title="Chapter", file_name="chapter.xhtml")
    chapter.content = "<html><body><h1>Test</h1></body></html>"
    book.add_item(chapter)
    book.toc = (epub.Link("chapter.xhtml", "Chapter", "chapter"),)
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(epub_path), book)

    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "Alpha PDF", "/Author": "QA Author"})
    with pdf_path.open("wb") as output:
        writer.write(output)

    adapter = EbookAdapter()
    epub_metadata = adapter.read_metadata(epub_path)
    pdf_metadata = adapter.read_metadata(pdf_path)

    assert epub_metadata["parse_status"] == "success"
    assert epub_metadata["title"] == "Alpha EPUB"
    assert epub_metadata["author"] == "QA Author"
    assert pdf_metadata["parse_status"] == "success"
    assert pdf_metadata["title"] == "Alpha PDF"
    assert pdf_metadata["author"] == "QA Author"
    assert pdf_metadata["pages"] == 1
    assert adapter.supports_preview() is False


def test_ebook_adapter_handles_mobi_metadata_reader(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import ebookatty

    mobi_path = tmp_path / "sample.mobi"
    mobi_path.write_bytes(b"mobi fixture consumed by the mocked parser")

    class FakeMetadataFetcher:
        def extract_metadata(self, _path: str) -> dict[str, str]:
            return {"title": "Alpha MOBI", "author": "QA Author"}

    monkeypatch.setattr(ebookatty, "MetadataFetcher", FakeMetadataFetcher)

    metadata = EbookAdapter().read_metadata(mobi_path)

    assert metadata["parse_status"] == "success"
    assert metadata["title"] == "Alpha MOBI"
    assert metadata["author"] == "QA Author"
    assert metadata["metadata_extracted"] is True
