"""
PDF loader tests use a minimal in-memory PDF created with PyMuPDF.
No external fixture file needed.
"""

import hashlib
from pathlib import Path

import fitz
import pytest

from core.model.document import Page
from infrastructure.ingest.pdf_loader import _is_chapter_heading, _synthetic_chapters, load_pdf


@pytest.fixture()
def simple_pdf(tmp_path: Path) -> Path:
    """Create a minimal 3-page PDF."""
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} content. " * 20)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def chapter_pdf(tmp_path: Path) -> Path:
    """Create a PDF with chapter headings."""
    pdf_path = tmp_path / "chapters.pdf"
    doc = fitz.open()

    for ch in range(1, 4):
        page = doc.new_page()
        page.insert_text((72, 72), f"Chapter {ch}\n\n" + "Some content here. " * 30)
        # Body page
        page2 = doc.new_page()
        page2.insert_text((72, 72), "More body content. " * 40)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_load_pdf_returns_document(simple_pdf):
    doc = load_pdf(simple_pdf, _hash(simple_pdf))
    assert doc.source_path == str(simple_pdf)
    assert doc.file_hash != ""
    assert len(doc.chapters) >= 1


def test_load_pdf_page_count(simple_pdf):
    doc = load_pdf(simple_pdf, _hash(simple_pdf))
    total_pages = sum(len(ch.pages) for ch in doc.chapters)
    assert total_pages == 3


def test_chapter_detection(chapter_pdf):
    doc = load_pdf(chapter_pdf, _hash(chapter_pdf))
    # Should detect 3 chapters (Chapter 1, 2, 3)
    assert len(doc.chapters) >= 2


def test_synthetic_chapters():
    pages = [Page(number=i, text=f"text {i}") for i in range(50)]
    chapters = _synthetic_chapters(pages)
    assert len(chapters) >= 2
    # Each chapter has at most 20 pages
    for ch in chapters:
        assert len(ch.pages) <= 20


@pytest.fixture()
def word_chapter_pdf(tmp_path: Path) -> Path:
    """Create a PDF with written-out chapter headings."""
    pdf_path = tmp_path / "word_chapters.pdf"
    doc = fitz.open()

    headings = ["CHAPTER ONE", "CHAPTER TWO", "CHAPTER THREE"]
    for heading in headings:
        page = doc.new_page()
        page.insert_text((72, 72), f"{heading}\n\n" + "Some content here. " * 30)
        page2 = doc.new_page()
        page2.insert_text((72, 72), "More body content. " * 40)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_chapter_detection_word_ordinals(word_chapter_pdf):
    """Written-out ordinals like CHAPTER ONE should be detected."""
    doc = load_pdf(word_chapter_pdf, _hash(word_chapter_pdf))
    assert len(doc.chapters) >= 2


def test_chapter_heading_word_ordinal_variants():
    """Verify _is_chapter_heading matches various written-out formats."""
    assert _is_chapter_heading("CHAPTER ONE\nSome text")[0]
    assert _is_chapter_heading("Chapter Two\nSome text")[0]
    assert _is_chapter_heading("chapter three\nSome text")[0]
    assert _is_chapter_heading("CHAPTER TWENTY-ONE\nSome text")[0]
    assert _is_chapter_heading("Chapter Twenty One\nSome text")[0]
    # Existing numeric patterns still work
    assert _is_chapter_heading("Chapter 1\nSome text")[0]
    assert _is_chapter_heading("Chapter 42\nSome text")[0]
    # Non-chapter text should not match
    assert not _is_chapter_heading("The one chapter\nSome text")[0]
    assert not _is_chapter_heading("Once upon a time\nSome text")[0]


def test_chapter_heading_numbered_variants():
    """Verify _is_chapter_heading matches numbered formats."""
    assert _is_chapter_heading("Chapter 1: Introduction\nText")[0]
    assert _is_chapter_heading("CHAPTER 2 Introduction\nText")[0]
    assert _is_chapter_heading("1. Introduction\nText")[0]
    assert _is_chapter_heading("1 Introduction\nText")[0]
    assert _is_chapter_heading("12. Methods\nText")[0]
    assert _is_chapter_heading("1.2 Introduction\nText")[0]


def test_chapter_heading_part_sections():
    """Verify _is_chapter_heading matches Part and Section patterns."""
    assert _is_chapter_heading("Part I\nText")[0]
    assert _is_chapter_heading("Part 1: Summary\nText")[0]
    assert _is_chapter_heading("PART III Summary\nText")[0]
    assert _is_chapter_heading("Section 1\nText")[0]
    assert _is_chapter_heading("SECTION 2 Introduction\nText")[0]


def test_chapter_heading_uppercase_standalone():
    """Verify _is_chapter_heading matches standalone uppercase headings."""
    assert _is_chapter_heading("CHAPTER\nText")[0]
    assert _is_chapter_heading("PREFACE\nText")[0]
    assert _is_chapter_heading("REFERENCES\nText")[0]
    assert _is_chapter_heading("APPENDIX\nText")[0]


def test_single_chapter_document():
    """A document with only one chapter should be named 'Document', not 'Introduction'."""
    pages = [
        Page(number=1, text="Article Title\n\nSome article content. " * 20),
        Page(number=2, text="More article content. " * 20),
    ]
    from infrastructure.ingest.pdf_loader import _detect_chapters

    chapters = _detect_chapters(pages)
    assert len(chapters) == 1
    assert chapters[0].title == "Document"
