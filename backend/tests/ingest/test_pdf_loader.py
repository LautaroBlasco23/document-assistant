"""
PDF loader tests use a minimal in-memory PDF created with PyMuPDF.
No external fixture file needed.
"""

import hashlib
from pathlib import Path

import fitz
import pytest

from core.model.document import Chapter, Page
from infrastructure.ingest.pdf_loader import (
    _is_chapter_heading,
    _synthetic_chapters,
    _toc_confidence,
    _validate_toc_page,
    load_pdf,
)


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


@pytest.fixture()
def offset_toc_pdf(tmp_path: Path) -> Path:
    """Create a 7-page PDF where ToC page numbers are offset by 3 front-matter pages.

    Pages 1-3: front matter (no chapter headings)
    Pages 4-5: "Introduction to the Subject" chapter
    Pages 6-7: "Research Methods" chapter
    ToC says: Introduction→1, Methods→4 (both wrong, offset by 3).
    """
    pdf_path = tmp_path / "offset_toc.pdf"
    doc = fitz.open()

    # Pages 1-3: front matter
    for _ in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), "Front matter content. " * 15)

    # Pages 4-5: Chapter 1
    page = doc.new_page()
    page.insert_text((72, 72), "Introduction to the Subject\n\n" + "Chapter content. " * 30)
    page = doc.new_page()
    page.insert_text((72, 72), "More introduction content. " * 30)

    # Pages 6-7: Chapter 2
    page = doc.new_page()
    page.insert_text((72, 72), "Research Methods\n\n" + "Methods content. " * 30)
    page = doc.new_page()
    page.insert_text((72, 72), "More methods content. " * 30)

    # Set ToC with wrong page numbers (offset by -3)
    doc.set_toc([
        [1, "Introduction to the Subject", 1],
        [1, "Research Methods", 4],
    ])

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def accurate_toc_pdf(tmp_path: Path) -> Path:
    """Create a 4-page PDF where ToC page numbers are correct."""
    pdf_path = tmp_path / "accurate_toc.pdf"
    doc = fitz.open()

    page = doc.new_page()
    page.insert_text((72, 72), "Chapter One: Introduction\n\n" + "Introduction text. " * 30)
    page = doc.new_page()
    page.insert_text((72, 72), "More introduction text. " * 30)

    page = doc.new_page()
    page.insert_text((72, 72), "Chapter Two: Methods\n\n" + "Methods text. " * 30)
    page = doc.new_page()
    page.insert_text((72, 72), "More methods text. " * 30)

    doc.set_toc([
        [1, "Chapter One: Introduction", 1],
        [1, "Chapter Two: Methods", 3],
    ])

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_toc_page_validation_corrects_offset(offset_toc_pdf):
    """ToC page numbers offset by front matter should be corrected."""
    doc = load_pdf(offset_toc_pdf, _hash(offset_toc_pdf))
    assert len(doc.chapters) == 2
    ch1, ch2 = doc.chapters

    assert ch1.title == "Introduction to the Subject"
    assert ch1.pages[0].number == 4
    assert ch1.pages[-1].number == 5

    assert ch2.title == "Research Methods"
    assert ch2.pages[0].number == 6
    assert ch2.pages[-1].number == 7


def test_accurate_toc_unchanged(accurate_toc_pdf):
    """Correct ToC page numbers should pass through unchanged."""
    doc = load_pdf(accurate_toc_pdf, _hash(accurate_toc_pdf))
    assert len(doc.chapters) == 2
    ch1, ch2 = doc.chapters

    assert ch1.title == "Chapter One: Introduction"
    assert ch1.pages[0].number == 1
    assert ch1.pages[-1].number == 2

    assert ch2.title == "Chapter Two: Methods"
    assert ch2.pages[0].number == 3
    assert ch2.pages[-1].number == 4


def test_validate_toc_page_finds_correct_page():
    """_validate_toc_page should find the correct page when ToC page is wrong."""
    pages = [
        Page(number=1, text="Front matter\n\nSome intro text."),
        Page(number=2, text="More front matter."),
        Page(number=3, text="PREFACE\n\nPreface content."),
        Page(number=4, text="Introduction to the Subject\n\nReal content starts here."),
        Page(number=5, text="More real content for chapter one."),
    ]
    corrected = _validate_toc_page(
        toc_page=1, chapter_title="Introduction to the Subject", pages=pages
    )
    assert corrected == 4


def test_validate_toc_page_fallback():
    """When no page matches the title, return original ToC page number."""
    pages = [
        Page(number=1, text="Random content."),
        Page(number=2, text="More random content."),
    ]
    corrected = _validate_toc_page(
        toc_page=1, chapter_title="Nonexistent Chapter Title", pages=pages
    )
    assert corrected == 1


def test_toc_confidence_non_overlapping():
    """Non-overlapping chapters with matching titles should have high confidence."""
    chapters = [
        Chapter(index=0, title="Introduction", pages=[
            Page(number=1, text="Introduction\n\nContent here."),
            Page(number=2, text="More content."),
        ]),
        Chapter(index=1, title="Methods", pages=[
            Page(number=3, text="Methods\n\nMethod details."),
            Page(number=4, text="More methods."),
        ]),
    ]
    pages = [p for ch in chapters for p in ch.pages]
    score = _toc_confidence(chapters, pages)
    assert score >= 0.5


def test_toc_confidence_overlapping():
    """Overlapping chapters with missing title matches should have low confidence."""
    chapters = [
        Chapter(index=0, title="Introduction", pages=[
            Page(number=1, text="Random preamble text without the title word."),
            Page(number=3, text="Overlapping content."),
        ]),
        Chapter(index=1, title="Methods", pages=[
            Page(number=2, text="Miscellaneous content without the title word."),
            Page(number=4, text="More methods content."),
        ]),
    ]
    pages = [p for ch in chapters for p in ch.pages]
    score = _toc_confidence(chapters, pages)
    assert score < 0.5


def test_preview_import_consistency(chapter_pdf):
    """Preview and full import should produce same chapter boundaries."""
    from infrastructure.ingest.pdf_loader import preview_pdf

    _, preview_chapters = preview_pdf(chapter_pdf, _hash(chapter_pdf))
    doc = load_pdf(chapter_pdf, _hash(chapter_pdf))

    assert len(preview_chapters) == len(doc.chapters)
    for prev_ch, doc_ch in zip(preview_chapters, doc.chapters):
        assert prev_ch.title == doc_ch.title
        assert prev_ch.page_start == doc_ch.pages[0].number
        assert prev_ch.page_end == doc_ch.pages[-1].number


def test_toc_low_confidence_triggers_fallback_to_heuristic(tmp_path: Path):
    """When ToC has overlapping page ranges, fall back to heuristic detection."""
    pdf_path = tmp_path / "bad_toc.pdf"
    doc = fitz.open()

    page = doc.new_page()
    page.insert_text((72, 72), "Chapter 1\n\nContent for chapter 1. " * 20)
    page = doc.new_page()
    page.insert_text((72, 72), "More chapter 1 content. " * 20)
    page = doc.new_page()
    page.insert_text((72, 72), "Chapter 2\n\nContent for chapter 2. " * 20)
    page = doc.new_page()
    page.insert_text((72, 72), "More chapter 2 content. " * 20)

    # ToC with overlapping page ranges: both chapters claim page 1
    doc.set_toc([
        [1, "Chapter 1", 1],
        [1, "Chapter 2", 1],
    ])

    doc.save(str(pdf_path))
    doc.close()

    result = load_pdf(pdf_path, _hash(pdf_path))
    assert len(result.chapters) == 2
    # After fallback, chapters should be detected by heading pattern
    assert result.chapters[0].title == "Chapter 1"
    assert result.chapters[1].title == "Chapter 2"
    # Ranges should not overlap
    assert result.chapters[0].pages[-1].number < result.chapters[1].pages[0].number


def test_minimum_chapter_size_enforced():
    """Chapters with fewer than 2 pages should be merged into the previous chapter."""
    from infrastructure.ingest.pdf_loader import _detect_chapters

    pages = [
        Page(number=1, text="Chapter 1\n\nContent for chapter 1."),
        Page(number=2, text="More chapter 1 content."),
        Page(number=3, text="Chapter 2\n\nSingle page chapter."),
        Page(number=4, text="Chapter 3\n\nContent for chapter 3."),
        Page(number=5, text="More chapter 3 content."),
    ]
    chapters = _detect_chapters(pages)
    # Chapter 2 (1 page) should be merged into the first chapter
    assert len(chapters) == 2
    # First chapter starts with default title "Introduction"
    assert chapters[0].title == "Introduction"
    # First chapter should now have 3 pages (1, 2, 3)
    assert len(chapters[0].pages) == 3
    assert chapters[1].title == "Chapter 3"
    assert len(chapters[1].pages) == 2


def test_heading_detection_only_first_two_lines():
    """Headings on line 3+ should not trigger a chapter split."""
    # Heading appears on line 3 (index 2) -- should NOT match with lines[:2]
    text = "Some preamble text.\nAnother line here.\nChapter 1: Introduction\nContent follows."
    is_heading, line_idx = _is_chapter_heading(text)
    assert not is_heading
    assert line_idx == -1

    # Heading on line 1 should still match
    text2 = "Chapter 1: Introduction\n\nContent follows."
    is_heading2, _ = _is_chapter_heading(text2)
    assert is_heading2


def test_toc_validation_preview_corrects_offset(offset_toc_pdf):
    """Preview should validate and correct ToC page numbers, same as full load."""
    from infrastructure.ingest.pdf_loader import preview_pdf

    _, preview_chapters = preview_pdf(offset_toc_pdf, _hash(offset_toc_pdf))
    assert len(preview_chapters) == 2
    ch1, ch2 = preview_chapters

    assert ch1.title == "Introduction to the Subject"
    assert ch1.page_start == 4
    assert ch1.page_end == 5

    assert ch2.title == "Research Methods"
    assert ch2.page_start == 6
    assert ch2.page_end == 7
