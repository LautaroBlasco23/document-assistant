"""
PDF loader tests use a minimal in-memory PDF created with PyMuPDF.
No external fixture file needed.
"""
import hashlib
from pathlib import Path

import fitz
import pytest

from core.model.document import Page
from infrastructure.ingest.pdf_loader import _synthetic_chapters, load_pdf


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
