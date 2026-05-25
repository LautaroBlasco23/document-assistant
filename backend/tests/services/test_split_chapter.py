"""Tests for split_chapter_into_ranges service function."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import fitz
import pytest

from api.schemas.knowledge_tree import ChapterSplitEntry
from api.services import Services
from application.services.tree_import import split_chapter_into_ranges


@pytest.fixture()
def chapter_pdf(tmp_path: Path) -> Path:
    """Create a 6-page chapter PDF."""
    pdf_path = tmp_path / "chapter.pdf"
    doc = fitz.open()
    for i in range(6):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} content. " * 20)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _make_chapter_mock(number=1, title="Chapter 1"):
    m = MagicMock()
    m.id = uuid4()
    m.number = number
    m.title = title
    return m


@pytest.fixture()
def mock_services(chapter_pdf: Path) -> tuple:
    """Create mock services with a pre-populated tree/chapter/doc."""
    tree_id = uuid4()
    chapter_id = uuid4()
    doc_id = uuid4()

    services = MagicMock(spec=Services)
    services.kt_chapter_store = MagicMock()
    services.kt_doc_store = MagicMock()
    services.kt_content_store = MagicMock()

    mock_chapter = MagicMock()
    mock_chapter.id = chapter_id
    mock_chapter.number = 1
    mock_chapter.title = "Chapter 1"
    services.kt_chapter_store.list_chapters.return_value = [mock_chapter]

    def _create_chapter_with_number(tree_id, number, title):
        m = MagicMock()
        m.id = uuid4()
        m.number = number
        m.title = title
        return m
    services.kt_chapter_store.create_chapter_with_number.side_effect = _create_chapter_with_number

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.source_file_path = str(chapter_pdf)
    mock_doc.source_file_name = "chapter.pdf"
    mock_doc.page_start = 1
    mock_doc.page_end = 6
    mock_doc.title = "Chapter 1"
    services.kt_doc_store.list_documents.return_value = [mock_doc]

    new_doc_mock = MagicMock()
    new_doc_mock.id = uuid4()
    services.kt_doc_store.create_document.return_value = new_doc_mock

    return services, tree_id, chapter_id, doc_id


def test_split_into_3_chapters(mock_services, tmp_path):
    """Basic 3-way split creates correct chapters."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=1, title="Part 1"),
        ChapterSplitEntry(page_start=2, page_end=3, title="Part 2"),
        ChapterSplitEntry(page_start=4, page_end=5, title="Part 3"),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        result = split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    assert len(result) == 3
    assert result[0].title == "Chapter 1"  # original chapter title preserved
    assert result[1].title == "Part 2"
    assert result[2].title == "Part 3"
    assert services.kt_chapter_store.shift_chapter_numbers.called
    assert services.kt_chapter_store.create_chapter_with_number.called


def test_split_preserves_content(mock_services, tmp_path):
    """Each segment gets correct page ranges and content."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=2),
        ChapterSplitEntry(page_start=3, page_end=5),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    update_call = services.kt_doc_store.update_document.call_args
    assert update_call is not None
    args, _ = update_call
    assert len(args) >= 3
    assert len(args[2]) > 0  # content is 3rd positional arg

    services.kt_doc_store.update_document_page_range.assert_called_once_with(
        doc_id, 1, 3
    )

    create_call = services.kt_doc_store.create_document.call_args
    assert create_call is not None
    _, kwargs = create_call
    assert kwargs["page_start"] == 4
    assert kwargs["page_end"] == 6


def test_split_updates_page_ranges(mock_services, tmp_path):
    """Original doc updated, new docs have correct ranges."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=1, title="First"),
        ChapterSplitEntry(page_start=2, page_end=3, title="Second"),
        ChapterSplitEntry(page_start=4, page_end=5, title="Third"),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    services.kt_doc_store.update_document_page_range.assert_called_once_with(
        doc_id, 1, 2
    )

    create_calls = services.kt_doc_store.create_document.call_args_list
    assert len(create_calls) == 2
    _, kwargs1 = create_calls[0]
    assert kwargs1["page_start"] == 3
    assert kwargs1["page_end"] == 4
    _, kwargs2 = create_calls[1]
    assert kwargs2["page_start"] == 5
    assert kwargs2["page_end"] == 6


def test_split_shifts_subsequent_chapters(mock_services, tmp_path):
    """Chapters after the split are renumbered."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=1),
        ChapterSplitEntry(page_start=2, page_end=3),
        ChapterSplitEntry(page_start=4, page_end=5),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    services.kt_chapter_store.shift_chapter_numbers.assert_called_once_with(
        tree_id, 2, 2
    )


def test_split_invalid_too_few_entries(mock_services):
    """Raises on < 2 entries."""
    services, tree_id, chapter_id, doc_id = mock_services

    with pytest.raises(ValueError, match="At least 2 chapter entries"):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=[ChapterSplitEntry(page_start=0, page_end=5)],
            services=services,
        )


def test_split_non_contiguous_ranges(mock_services, tmp_path):
    """Raises on gaps between entries."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=1),
        ChapterSplitEntry(page_start=3, page_end=5),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        with pytest.raises(ValueError, match="Non-contiguous"):
            split_chapter_into_ranges(
                tree_id=tree_id,
                chapter_number=1,
                chapters=entries,
                services=services,
            )


def test_split_exceeds_original_range(mock_services, tmp_path):
    """Raises when entries go beyond original document range."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=3),
        ChapterSplitEntry(page_start=4, page_end=7),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        with pytest.raises(ValueError, match="outside valid relative range"):
            split_chapter_into_ranges(
                tree_id=tree_id,
                chapter_number=1,
                chapters=entries,
                services=services,
            )


def test_split_incomplete_coverage(mock_services, tmp_path):
    """Raises when last entry doesn't reach original end."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=2),
        ChapterSplitEntry(page_start=3, page_end=4),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        with pytest.raises(ValueError, match=r"Last entry must end at relative page 5 \(document covers absolute pages 1–6\), got 4"):
            split_chapter_into_ranges(
                tree_id=tree_id,
                chapter_number=1,
                chapters=entries,
                services=services,
            )


def test_split_requires_pdf_or_epub(mock_services):
    """Raises on non-PDF/EPUB source."""
    services, tree_id, chapter_id, doc_id = mock_services

    doc = services.kt_doc_store.list_documents.return_value[0]
    doc.source_file_path = "/path/to/document.txt"

    with pytest.raises(ValueError, match="only supported for PDF and EPUB"):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=[
                ChapterSplitEntry(page_start=0, page_end=2),
                ChapterSplitEntry(page_start=3, page_end=5),
            ],
            services=services,
        )


def test_split_deletes_old_chunks(mock_services, tmp_path):
    """Old chunks cleaned up."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=2),
        ChapterSplitEntry(page_start=3, page_end=5),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    services.kt_content_store.delete_chunks_by_doc_id.assert_called_once_with(doc_id)


def test_split_saves_new_chunks(mock_services, tmp_path):
    """New chunks saved for all segments."""
    services, tree_id, chapter_id, doc_id = mock_services
    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=2),
        ChapterSplitEntry(page_start=3, page_end=5),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    services.kt_content_store.save_chunks.assert_called_once()


def test_split_pdf_content_with_offset_page_start(tmp_path):
    """PDF extraction uses relative offsets for sub-PDF when page_start > 1."""
    pdf_path = tmp_path / "chapter.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Content Page {6 + i + 1}." * 20)
    doc.save(str(pdf_path))
    doc.close()

    tree_id = uuid4()
    chapter_id = uuid4()
    doc_id = uuid4()

    services = MagicMock(spec=Services)
    services.kt_chapter_store = MagicMock()
    services.kt_doc_store = MagicMock()
    services.kt_content_store = MagicMock()

    mock_chapter = MagicMock()
    mock_chapter.id = chapter_id
    mock_chapter.number = 1
    mock_chapter.title = "Chapter 1"
    services.kt_chapter_store.list_chapters.return_value = [mock_chapter]

    def _create_chapter_with_number(tree_id, number, title):
        m = MagicMock()
        m.id = uuid4()
        m.number = number
        m.title = title
        return m
    services.kt_chapter_store.create_chapter_with_number.side_effect = _create_chapter_with_number

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.source_file_path = str(pdf_path)
    mock_doc.source_file_name = "chapter.pdf"
    mock_doc.page_start = 6
    mock_doc.page_end = 8
    mock_doc.title = "Chapter 1"
    services.kt_doc_store.list_documents.return_value = [mock_doc]

    new_doc_mock = MagicMock()
    new_doc_mock.id = uuid4()
    services.kt_doc_store.create_document.return_value = new_doc_mock

    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=1, title="First"),
        ChapterSplitEntry(page_start=2, page_end=2, title="Last"),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    update_calls = services.kt_doc_store.update_document_source_file.call_args_list
    assert len(update_calls) == 2

    args0, _ = update_calls[0]
    seg0 = fitz.open(str(Path(args0[1])))
    assert len(seg0) == 2
    assert "Content Page 7" in seg0[0].get_text()
    assert "Content Page 8" in seg0[1].get_text()
    seg0.close()

    args1, _ = update_calls[1]
    seg1 = fitz.open(str(Path(args1[1])))
    assert len(seg1) == 1
    assert "Content Page 9" in seg1[0].get_text()
    seg1.close()


def test_split_requires_page_range(mock_services):
    """Document without page range should raise ValueError."""
    services, tree_id, chapter_id, doc_id = mock_services

    doc = services.kt_doc_store.list_documents.return_value[0]
    doc.page_start = None

    with pytest.raises(ValueError, match="no page range information"):
        split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=[
                ChapterSplitEntry(page_start=0, page_end=2),
                ChapterSplitEntry(page_start=3, page_end=5),
            ],
            services=services,
        )


def test_split_produces_absolute_page_numbers_in_chunks(tmp_path):
    """Split produces documents with absolute page numbers, not relative 1-based."""
    pdf_path = tmp_path / "chapter.pdf"
    doc = fitz.open()
    for i in range(6):
        page = doc.new_page()
        page.insert_text((72, 72), f"Content for absolute page {10 + i}. " * 30)
    doc.save(str(pdf_path))
    doc.close()

    tree_id = uuid4()
    chapter_id = uuid4()
    doc_id = uuid4()

    services = MagicMock(spec=Services)
    services.kt_chapter_store = MagicMock()
    services.kt_doc_store = MagicMock()
    services.kt_content_store = MagicMock()

    mock_chapter = MagicMock()
    mock_chapter.id = chapter_id
    mock_chapter.number = 1
    mock_chapter.title = "Chapter 1"
    services.kt_chapter_store.list_chapters.return_value = [mock_chapter]

    def _create_chapter_with_number(tree_id, number, title):
        m = MagicMock()
        m.id = uuid4()
        m.number = number
        m.title = title
        return m
    services.kt_chapter_store.create_chapter_with_number.side_effect = _create_chapter_with_number

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.source_file_path = str(pdf_path)
    mock_doc.source_file_name = "chapter.pdf"
    mock_doc.page_start = 10
    mock_doc.page_end = 15
    mock_doc.title = "Chapter 1"
    services.kt_doc_store.list_documents.return_value = [mock_doc]

    new_doc_mock = MagicMock()
    new_doc_mock.id = uuid4()
    services.kt_doc_store.create_document.return_value = new_doc_mock

    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=2, title="Part 1"),
        ChapterSplitEntry(page_start=3, page_end=5, title="Part 2"),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        result = split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    assert len(result) == 2

    # First segment uses absolute page range 10-12, not 1-3
    services.kt_doc_store.update_document_page_range.assert_called_once_with(doc_id, 10, 12)

    # Second segment uses absolute page range 13-15
    create_calls = services.kt_doc_store.create_document.call_args_list
    assert len(create_calls) == 1
    _, kwargs = create_calls[0]
    assert kwargs["page_start"] == 13
    assert kwargs["page_end"] == 15

    # Verify chunk text contains content from correct absolute pages
    save_call = services.kt_content_store.save_chunks.call_args
    assert save_call is not None
    chunk_list = save_call[0][0]
    seg1_texts = [c.text for c in chunk_list if c.chapter_id == chapter_id]
    seg2_texts = [c.text for c in chunk_list if c.chapter_id != chapter_id]

    def _any_page_in(texts, pages):
        return any(f"absolute page {p}" in text for text in texts for p in pages)

    assert _any_page_in(seg1_texts, range(10, 13)), "Seg 1 should contain pages 10-12"
    assert _any_page_in(seg2_texts, range(13, 16)), "Seg 2 should contain pages 13-15"

    assert not _any_page_in(seg1_texts, range(13, 16)), "Seg 1 should not contain pages 13-15"
    assert not _any_page_in(seg2_texts, range(10, 13)), "Seg 2 should not contain pages 10-12"


def test_split_all_content_captured(tmp_path):
    """All page content is preserved across segments (no content loss)."""
    pdf_path = tmp_path / "chapter.pdf"
    doc = fitz.open()
    full_text_pages = []
    for i in range(6):
        page = doc.new_page()
        text = f"UNIQUE PAGE {i + 1} CONTENT. " * 30
        page.insert_text((72, 72), text)
        full_text_pages.append(text)
    doc.save(str(pdf_path))
    doc.close()

    tree_id = uuid4()
    chapter_id = uuid4()
    doc_id = uuid4()

    services = MagicMock(spec=Services)
    services.kt_chapter_store = MagicMock()
    services.kt_doc_store = MagicMock()
    services.kt_content_store = MagicMock()

    mock_chapter = MagicMock()
    mock_chapter.id = chapter_id
    mock_chapter.number = 1
    mock_chapter.title = "Chapter 1"
    services.kt_chapter_store.list_chapters.return_value = [mock_chapter]

    def _create_chapter_with_number(tree_id, number, title):
        m = MagicMock()
        m.id = uuid4()
        m.number = number
        m.title = title
        return m
    services.kt_chapter_store.create_chapter_with_number.side_effect = _create_chapter_with_number

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.source_file_path = str(pdf_path)
    mock_doc.source_file_name = "chapter.pdf"
    mock_doc.page_start = 1
    mock_doc.page_end = 6
    mock_doc.title = "Chapter 1"
    services.kt_doc_store.list_documents.return_value = [mock_doc]

    new_doc_mock = MagicMock()
    new_doc_mock.id = uuid4()
    services.kt_doc_store.create_document.return_value = new_doc_mock

    test_storage = tmp_path / "data" / "storage"
    test_storage.mkdir(parents=True)

    entries = [
        ChapterSplitEntry(page_start=0, page_end=1, title="Part 1"),
        ChapterSplitEntry(page_start=2, page_end=3, title="Part 2"),
        ChapterSplitEntry(page_start=4, page_end=5, title="Part 3"),
    ]

    with patch("application.services.tree_import.PROJECT_ROOT", tmp_path):
        result = split_chapter_into_ranges(
            tree_id=tree_id,
            chapter_number=1,
            chapters=entries,
            services=services,
        )

    assert len(result) == 3

    # Collect all segment texts
    update_call = services.kt_doc_store.update_document.call_args
    assert update_call is not None
    seg1_text = update_call[0][2]

    create_calls = services.kt_doc_store.create_document.call_args_list
    assert len(create_calls) == 2
    seg2_text = create_calls[0][0][3]  # content is 4th positional arg
    seg3_text = create_calls[1][0][3]  # content is 4th positional arg

    all_text = seg1_text + seg2_text + seg3_text

    # All original content present
    for i in range(6):
        assert f"UNIQUE PAGE {i + 1} CONTENT" in all_text, f"Content from page {i + 1} is missing"
