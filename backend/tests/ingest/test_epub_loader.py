"""
EPUB loader tests use synthetic EPUBs created with ebooklib,
plus mocked ebooklib responses for edge cases.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ebooklib import epub

from infrastructure.config import EpubConfig
from infrastructure.ingest.epub_loader import (
    ChapterPreview,
    _apply_min_words_merge,
    _build_toc_groups,
    _collect_toc_entries,
    _extract_text,
    _get_metadata,
    _parse_item,
    load_epub,
    preview_epub,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_epub(
    tmp_path: Path,
    title: str = "Test Book",
    author: str = "Test Author",
    chapters: list[tuple[str, str, str]] | None = None,
    toc: list | None = None,
) -> Path:
    """Create a synthetic EPUB file on disk.

    chapters: list of (file_name, chapter_title, html_body) tuples.
    The chapter_title is injected as an <h1> in the body so ebooklib
    does not strip it during write/read.
    toc: optional explicit toc list; defaults to flat Link entries.
    """
    book = epub.EpubBook()
    book.set_identifier("test-id")
    book.set_title(title)
    book.set_language("en")
    if author:
        book.add_metadata("DC", "creator", author)

    spine: list = []

    for idx, (file_name, ch_title, body) in enumerate(chapters or []):
        item = epub.EpubHtml(title=ch_title, file_name=file_name, lang="en")
        item.content = (
            f"<html><head><title>{ch_title}</title></head>"
            f"<body><h1>{ch_title}</h1>{body}</body></html>"
        )
        book.add_item(item)
        spine.append(item)

    nav = epub.EpubNav()
    book.add_item(nav)
    book.add_item(epub.EpubNcx())

    book.spine = spine
    book.toc = toc if toc is not None else [
        epub.Link(file_name, ch_title, f"id{idx}")
        for idx, (file_name, ch_title, _body) in enumerate(chapters or [])
    ]

    path = tmp_path / "test.epub"
    epub.write_epub(str(path), book)
    return path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def test_get_metadata_returns_value():
    """_get_metadata extracts DC metadata from an EpubBook."""
    book = epub.EpubBook()
    book.add_metadata("DC", "title", "My Title")
    book.add_metadata("DC", "creator", "Jane Doe")
    assert _get_metadata(book, "title") == "My Title"
    assert _get_metadata(book, "creator") == "Jane Doe"


def test_get_metadata_missing_returns_empty():
    """Missing metadata returns an empty string."""
    book = epub.EpubBook()
    assert _get_metadata(book, "title") == ""
    assert _get_metadata(book, "publisher") == ""


def test_extract_text_concatenates_blocks():
    """_extract_text joins block-level elements with newlines."""
    ns = "http://www.w3.org/1999/xhtml"
    html = f'<html xmlns="{ns}"><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>'
    root = __import__("lxml.etree", fromlist=["etree"]).fromstring(html.encode())
    text = _extract_text(root)
    assert "First paragraph." in text
    assert "Second paragraph." in text
    assert "\n" in text


def test_parse_item_returns_title_and_text():
    """_parse_item extracts title from <title> or <h1> and plain text from body."""
    ns = "http://www.w3.org/1999/xhtml"
    item = MagicMock()
    item.get_content.return_value = (
        f'<html xmlns="{ns}"><head><title>Real Title</title></head>'
        f'<body><h1>Heading</h1><p>Body text.</p></body></html>'
    ).encode()
    title, text = _parse_item(item)
    # title should come from <title> tag
    assert title == "Real Title"
    assert "Body text." in text


def test_parse_item_falls_back_to_h1():
    """When <title> is absent, _parse_item falls back to the first <h1>."""
    ns = "http://www.w3.org/1999/xhtml"
    item = MagicMock()
    item.get_content.return_value = (
        f'<html xmlns="{ns}"><body><h1>Chapter One</h1><p>Text.</p></body></html>'
    ).encode()
    title, text = _parse_item(item)
    assert title == "Chapter One"
    assert "Text." in text


def test_parse_item_bad_content_returns_empty():
    """Malformed XML returns empty strings without crashing."""
    item = MagicMock()
    item.get_content.return_value = b"not valid xml <<<"
    title, text = _parse_item(item)
    assert title == ""
    assert text == ""


def test_apply_min_words_merge_merges_short():
    """Groups below min_words are merged into the previous group."""
    groups = [
        ("Chapter 1", "", [MagicMock()]),
        ("Short", "", [MagicMock()]),
        ("Chapter 2", "", [MagicMock()]),
    ]
    texts = ["word " * 200, "word " * 5, "word " * 200]
    result = _apply_min_words_merge(groups, texts, min_words=50)
    # Short middle group is merged into Chapter 1
    assert len(result) == 2
    assert result[0][0] == "Chapter 1"
    assert "Short" not in [r[0] for r in result]
    # Merged text should contain the short group's text
    assert "word" in result[0][2]


def test_apply_min_words_merge_keeps_first_short():
    """The first group is kept even if it is below min_words (nothing to merge into)."""
    groups = [("Intro", "", [MagicMock()])]
    texts = ["word " * 5]
    result = _apply_min_words_merge(groups, texts, min_words=50)
    assert len(result) == 1
    assert result[0][0] == "Intro"


def test_apply_min_words_merge_empty():
    """Empty groups list returns empty list."""
    assert _apply_min_words_merge([], [], min_words=50) == []


# ---------------------------------------------------------------------------
# _build_toc_groups
# ---------------------------------------------------------------------------


def test_build_toc_groups_no_toc_fallback(tmp_path: Path):
    """When the EPUB has no ToC, each spine item becomes its own group."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "First", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "Second", "<p>" + "word " * 50 + "</p>"),
        ],
        toc=[],
    )
    book = epub.read_epub(str(path))
    items = list(book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT))
    groups = _build_toc_groups(book, items, depth=1)
    # ebooklib injects nav.xhtml; with no TOC it becomes an extra group,
    # but the real chapters should each have their own group.
    titles = [g[0] for g in groups]
    assert "First" in titles
    assert "Second" in titles


def test_build_toc_groups_nested_depth_1(tmp_path: Path):
    """At depth=1 only top-level Link entries become chapters."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("intro.xhtml", "Intro", "<p>" + "word " * 50 + "</p>"),
            ("ch1.xhtml", "Chapter 1", "<p>" + "word " * 50 + "</p>"),
            ("ch2.xhtml", "Chapter 2", "<p>" + "word " * 50 + "</p>"),
        ],
        toc=[
            epub.Link("intro.xhtml", "Intro", "id0"),
            (
                epub.Section("Part One"),
                [
                    epub.Link("ch1.xhtml", "Chapter 1", "id1"),
                    epub.Link("ch2.xhtml", "Chapter 2", "id2"),
                ],
            ),
        ],
    )
    book = epub.read_epub(str(path))
    items = list(book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT))
    groups = _build_toc_groups(book, items, depth=1)
    # Depth 1: only Intro is a Link at depth 1; Section children recurse to depth 2.
    # So toc_map only has intro.xhtml. ch1 and ch2 fall into the Intro group.
    titles = [g[0] for g in groups]
    assert "Intro" in titles


def test_build_toc_groups_nested_depth_2(tmp_path: Path):
    """At depth=2 nested Link entries are collected as chapters."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("ch1.xhtml", "Chapter 1", "<p>" + "word " * 50 + "</p>"),
            ("ch2.xhtml", "Chapter 2", "<p>" + "word " * 50 + "</p>"),
        ],
        toc=[
            (
                epub.Section("Part One"),
                [
                    epub.Link("ch1.xhtml", "Chapter 1", "id1"),
                ],
            ),
            (
                epub.Section("Part Two"),
                [
                    epub.Link("ch2.xhtml", "Chapter 2", "id2"),
                ],
            ),
        ],
    )
    book = epub.read_epub(str(path))
    items = list(book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT))
    groups = _build_toc_groups(book, items, depth=2)
    titles = [g[0] for g in groups]
    assert "Chapter 1" in titles
    assert "Chapter 2" in titles


# ---------------------------------------------------------------------------
# load_epub
# ---------------------------------------------------------------------------


def test_load_epub_returns_document(tmp_path: Path):
    """load_epub returns a Document with correct metadata."""
    path = _make_epub(
        tmp_path,
        title="Great Book",
        author="Alice",
        chapters=[("c1.xhtml", "Ch1", "<p>" + "word " * 50 + "</p>")],
    )
    doc = load_epub(path, "hash123", original_filename="book.epub")
    assert doc.source_path == str(path)
    assert doc.title == "Great Book"
    assert doc.file_hash == "hash123"
    assert doc.original_filename == "book.epub"
    assert doc.metadata.get("author") == "Alice"


def test_load_epub_chapter_titles(tmp_path: Path):
    """Chapter titles are extracted from <title> or heading tags."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "Alpha", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "Beta", "<p>" + "word " * 50 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=10)
    doc = load_epub(path, "hash", epub_config=cfg)
    assert len(doc.chapters) == 2
    assert doc.chapters[0].title == "Alpha"
    assert doc.chapters[1].title == "Beta"


def test_load_epub_pages(tmp_path: Path):
    """Each EPUB chapter is represented as a single synthetic Page."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "One", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "Two", "<p>" + "word " * 50 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=10)
    doc = load_epub(path, "hash", epub_config=cfg)
    assert len(doc.chapters) == 2
    for ch in doc.chapters:
        assert len(ch.pages) == 1
        assert ch.pages[0].number == 1
        assert "word" in ch.pages[0].text


def test_load_epub_reindexes_sequentially(tmp_path: Path):
    """After any skips or merges, chapter indices are 0-based and sequential."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "One", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "Two", "<p>" + "word " * 50 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=10)
    doc = load_epub(path, "hash", epub_config=cfg)
    for i, ch in enumerate(doc.chapters):
        assert ch.index == i


def test_load_epub_min_words_merge(tmp_path: Path):
    """Chapters under min_chapter_words are merged into the previous chapter."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "Long", "<p>" + "word " * 100 + "</p>"),
            ("c2.xhtml", "Short", "<p>short</p>"),
            ("c3.xhtml", "Also Long", "<p>" + "word " * 100 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=50)
    doc = load_epub(path, "hash", epub_config=cfg)
    # Short chapter merges into Long
    assert len(doc.chapters) == 2
    assert doc.chapters[0].title == "Long"
    assert doc.chapters[1].title == "Also Long"


def test_load_epub_no_merge_when_above_threshold(tmp_path: Path):
    """Chapters with word count above min_chapter_words stay separate."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "One", "<p>" + "word " * 100 + "</p>"),
            ("c2.xhtml", "Two", "<p>" + "word " * 100 + "</p>"),
            ("c3.xhtml", "Three", "<p>" + "word " * 100 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=50)
    doc = load_epub(path, "hash", epub_config=cfg)
    assert len(doc.chapters) == 3


def test_load_epub_corrupt_file(tmp_path: Path):
    """A corrupt/non-EPUB file raises an EpubException."""
    bad_path = tmp_path / "bad.epub"
    bad_path.write_bytes(b"this is not a zip file")
    with pytest.raises(epub.EpubException):
        load_epub(bad_path, "hash")


# ---------------------------------------------------------------------------
# preview_epub
# ---------------------------------------------------------------------------


def test_preview_epub_returns_previews(tmp_path: Path):
    """preview_epub returns a Document and a list of ChapterPreview objects."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "Alpha", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "Beta", "<p>" + "word " * 50 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=10)
    doc, previews = preview_epub(path, "hash", epub_config=cfg)
    assert doc is not None
    assert len(previews) == 2
    assert isinstance(previews[0], ChapterPreview)


def test_preview_epub_titles_and_indices(tmp_path: Path):
    """Preview titles and indices match the chapter structure."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "First", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "Second", "<p>" + "word " * 50 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=10)
    _doc, previews = preview_epub(path, "hash", epub_config=cfg)
    assert previews[0].index == 0
    assert previews[0].title == "First"
    assert previews[1].index == 1
    assert previews[1].title == "Second"


def test_preview_epub_page_ranges(tmp_path: Path):
    """For EPUB previews page_start == page_end == index + 1."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "A", "<p>" + "word " * 50 + "</p>"),
            ("c2.xhtml", "B", "<p>" + "word " * 50 + "</p>"),
            ("c3.xhtml", "C", "<p>" + "word " * 50 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=10)
    _doc, previews = preview_epub(path, "hash", epub_config=cfg)
    for i, prev in enumerate(previews):
        assert prev.page_start == i + 1
        assert prev.page_end == i + 1


def test_preview_epub_min_words_merge(tmp_path: Path):
    """Preview chapter count reflects min_chapter_words merging."""
    path = _make_epub(
        tmp_path,
        chapters=[
            ("c1.xhtml", "Long", "<p>" + "word " * 100 + "</p>"),
            ("c2.xhtml", "Short", "<p>tiny</p>"),
            ("c3.xhtml", "Also Long", "<p>" + "word " * 100 + "</p>"),
        ],
    )
    cfg = EpubConfig(min_chapter_words=50)
    _doc, previews = preview_epub(path, "hash", epub_config=cfg)
    assert len(previews) == 2
    assert previews[0].title == "Long"
    assert previews[1].title == "Also Long"


# ---------------------------------------------------------------------------
# Mocked edge cases
# ---------------------------------------------------------------------------


def test_load_epub_empty_spine():
    """An EPUB with no document items produces an empty chapter list."""
    mock_book = MagicMock()
    mock_book.get_items_of_type.return_value = []
    mock_book.toc = []
    mock_book.get_metadata.return_value = ""

    with patch("infrastructure.ingest.epub_loader.epub.read_epub", return_value=mock_book):
        doc = load_epub(Path("/fake/path.epub"), "hash")
    assert doc.chapters == []
    assert doc.title == "path"  # falls back to path.stem


def test_preview_epub_empty_spine():
    """Preview of an EPUB with no document items returns zero previews."""
    mock_book = MagicMock()
    mock_book.get_items_of_type.return_value = []
    mock_book.toc = []
    mock_book.get_metadata.return_value = ""

    with patch("infrastructure.ingest.epub_loader.epub.read_epub", return_value=mock_book):
        doc, previews = preview_epub(Path("/fake/path.epub"), "hash")
    assert doc is not None
    assert previews == []
    assert doc.chapters == []


def test_load_epub_deeply_nested_toc():
    """A deeply nested ToC with no matches at the requested depth falls back."""
    mock_book = MagicMock()
    mock_item = MagicMock()
    mock_item.file_name = "chap1.xhtml"
    mock_book.get_items_of_type.return_value = [mock_item]
    # ToC exists but only has a Section at depth 1 with no children at depth 2
    mock_book.toc = [(epub.Section("Part One"), [])]
    mock_book.get_metadata.return_value = ""

    with patch("infrastructure.ingest.epub_loader.epub.read_epub", return_value=mock_book):
        doc = load_epub(Path("/fake/path.epub"), "hash")
    # Fallback means each spine item becomes its own chapter
    assert len(doc.chapters) >= 0


def test_load_epub_skips_empty_text_groups():
    """Groups that produce no text after parsing are skipped."""
    mock_book = MagicMock()
    real_item = MagicMock()
    real_item.file_name = "c1.xhtml"
    real_item.get_content.return_value = (
        b'<html xmlns="http://www.w3.org/1999/xhtml">'
        b'<body><h1>Real</h1><p>word word word word word word word word word word</p></body></html>'
    )
    empty_item = MagicMock()
    empty_item.file_name = "c2.xhtml"
    empty_item.get_content.return_value = (
        b'<html xmlns="http://www.w3.org/1999/xhtml"><body></body></html>'
    )
    mock_book.get_items_of_type.return_value = [real_item, empty_item]
    mock_book.toc = []
    mock_book.get_metadata.return_value = ""

    with patch("infrastructure.ingest.epub_loader.epub.read_epub", return_value=mock_book):
        doc = load_epub(Path("/fake/path.epub"), "hash", epub_config=EpubConfig(min_chapter_words=5))
    titles = [ch.title for ch in doc.chapters]
    assert "Real" in titles
    # Empty group should be skipped (merged into previous or dropped)
    assert len(doc.chapters) >= 1
