import logging
from dataclasses import dataclass
from pathlib import Path

import ebooklib
from ebooklib import epub
from lxml import etree

from core.model.document import Chapter, Document, Page
from infrastructure.ingest.normalizer import normalize

logger = logging.getLogger(__name__)


@dataclass
class ChapterPreview:
    """Lightweight chapter metadata without full page text."""

    index: int
    title: str
    page_start: int  # 1-based (EPUB has no page concept, use index + 1)
    page_end: int


def preview_epub(path: Path, file_hash: str) -> tuple[Document | None, list[ChapterPreview]]:
    """Extract chapter structure from an EPUB without loading full page text.

    Returns (doc, chapters) where doc has no populated chapters (just metadata).
    chapters is the list of ChapterPreview objects.
    """
    book = epub.read_epub(str(path), options={"ignore_ncx": True})

    title = _get_metadata(book, "title") or path.stem
    author = _get_metadata(book, "creator") or ""

    chapters: list[ChapterPreview] = []
    idx = 0
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        chapter_title = _extract_title_only(item)
        chapters.append(
            ChapterPreview(
                index=idx,
                title=chapter_title or f"Chapter {idx + 1}",
                page_start=idx + 1,
                page_end=idx + 1,
            )
        )
        idx += 1

    result_doc = Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=path.name,
        chapters=[],  # Not populated - use full load for that
        metadata={"author": author},
    )

    logger.info("Preview EPUB %s: %d chapters", path.name, len(chapters))
    return result_doc, chapters


def _extract_title_only(item: epub.EpubItem) -> str:
    """Extract title from an EPUB item without loading full text."""
    try:
        content = item.get_content()
        root = etree.fromstring(content)
    except Exception:
        return ""

    title = ""
    title_el = root.find(".//{http://www.w3.org/1999/xhtml}title")
    if title_el is not None and title_el.text:
        title = title_el.text.strip()

    if not title:
        for tag in ("h1", "h2"):
            el = root.find(f".//{{{_XHTML}}}{{tag}}", {"tag": tag})
            if el is None:
                el = root.find(f".//{_XHTML}{tag}")
            if el is not None:
                title = "".join(el.itertext()).strip()
                break

    return title


def load_epub(path: Path, file_hash: str, original_filename: str = "") -> Document:
    """Extract a Document from an EPUB file."""
    book = epub.read_epub(str(path), options={"ignore_ncx": True})

    display_name = original_filename or path.name
    title = _get_metadata(book, "title") or Path(display_name).stem
    author = _get_metadata(book, "creator") or ""

    chapters: list[Chapter] = []
    for idx, item in enumerate(book.get_items_of_type(ebooklib.ITEM_DOCUMENT)):
        chapter_title, raw_text = _parse_item(item)
        if not raw_text.strip():
            continue

        normalized = normalize([raw_text])
        page = Page(number=1, text=normalized[0])
        chapters.append(
            Chapter(
                index=idx,
                title=chapter_title or f"Chapter {idx + 1}",
                pages=[page],
            )
        )

    # Re-index sequentially (some items may have been skipped)
    for i, ch in enumerate(chapters):
        ch.index = i

    logger.info("Loaded EPUB %s: %d chapters", display_name, len(chapters))
    return Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=original_filename or path.name,
        chapters=chapters,
        metadata={"author": author},
    )


def _get_metadata(book: epub.EpubBook, name: str) -> str:
    items = book.get_metadata("DC", name)
    if items:
        value = items[0]
        return value[0] if isinstance(value, tuple) else str(value)
    return ""


def _parse_item(item: epub.EpubItem) -> tuple[str, str]:
    """Return (title, plain_text) for an EPUB spine item."""
    try:
        content = item.get_content()
        root = etree.fromstring(content)
    except Exception:
        return "", ""

    # Extract title from <title> or first <h1>/<h2>
    title = ""
    title_el = root.find(".//{http://www.w3.org/1999/xhtml}title")
    if title_el is not None and title_el.text:
        title = title_el.text.strip()

    if not title:
        for tag in ("h1", "h2"):
            el = root.find(f".//{{{_XHTML}}}{{tag}}", {"tag": tag})
            if el is None:
                el = root.find(f".//{_XHTML}{tag}")
            if el is not None:
                title = "".join(el.itertext()).strip()
                break

    text = _extract_text(root)
    return title, text


_XHTML = "http://www.w3.org/1999/xhtml"

_BLOCK_TAGS = {
    f"{{{_XHTML}}}{t}"
    for t in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "td", "th")
}


def _extract_text(root: etree._Element) -> str:
    """Walk the element tree and concatenate text with newlines at block boundaries."""
    parts: list[str] = []

    def _walk(el: etree._Element) -> None:
        if el.tag in _BLOCK_TAGS:
            text = "".join(el.itertext()).strip()
            if text:
                parts.append(text)
        else:
            for child in el:
                _walk(child)

    _walk(root)
    return "\n".join(parts)
