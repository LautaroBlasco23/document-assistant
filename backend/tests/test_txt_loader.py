"""Unit tests for the TXT file loader."""

import tempfile
from pathlib import Path

import pytest

from infrastructure.ingest.txt_loader import (
    build_document_from_text,
    load_txt,
    preview_txt,
)


def _write_tmp(content: str, encoding: str = "utf-8", suffix: str = ".txt") -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", suffix=suffix, delete=False
    )
    tmp.write(content.encode(encoding))
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# build_document_from_text
# ---------------------------------------------------------------------------


def test_build_document_from_text_plain():
    """Plain text with no markers falls back to synthetic chapters."""
    text = " ".join(["word"] * 100)
    doc = build_document_from_text("Test", text, "abc123")
    assert doc.title == "Test"
    assert doc.file_hash == "abc123"
    assert len(doc.chapters) >= 1
    assert doc.chapters[0].title.startswith("Section")


def test_build_document_from_text_markdown_headers():
    text = "# Chapter 1\nContent of chapter 1.\n\n# Chapter 2\nContent of chapter 2.\n"
    doc = build_document_from_text("Book", text, "hash1")
    assert len(doc.chapters) == 2
    assert doc.chapters[0].title == "Chapter 1"
    assert doc.chapters[1].title == "Chapter 2"
    assert doc.chapters[0].index == 0
    assert doc.chapters[1].index == 1


def test_build_document_from_text_with_subsections():
    """## headers inside a # chapter become Section objects."""
    text = "# Chapter One\n## Intro\nIntro text\n## Details\nDetail text\n"
    doc = build_document_from_text("Book", text, "hash2")
    assert len(doc.chapters) == 1
    ch = doc.chapters[0]
    assert ch.title == "Chapter One"
    assert len(ch.sections) == 2
    assert ch.sections[0].title == "Intro"
    assert ch.sections[1].title == "Details"


def test_build_document_from_text_empty():
    """Empty content returns a Document with no chapters."""
    doc = build_document_from_text("Empty", "", "emptyhash")
    assert doc.chapters == []


def test_build_document_from_text_original_filename():
    doc = build_document_from_text("Title", "Some text here.", "h3", original_filename="notes.txt")
    assert doc.original_filename == "notes.txt"


# ---------------------------------------------------------------------------
# load_txt
# ---------------------------------------------------------------------------


def test_load_txt_plain_text():
    """Plain TXT file with no chapter markers produces synthetic chapters."""
    content = " ".join(["word"] * 200)
    path = _write_tmp(content)
    try:
        doc = load_txt(path, "filehash", "notes.txt")
        assert doc is not None
        assert doc.original_filename == "notes.txt"
        assert len(doc.chapters) >= 1
    finally:
        path.unlink()


def test_load_txt_markdown_headers():
    """TXT file with # markdown headers -> chapters."""
    content = "# Introduction\nSome intro text.\n\n# Chapter 1\nChapter 1 content.\n"
    path = _write_tmp(content)
    try:
        doc = load_txt(path, "hash_md", "study.txt")
        assert doc is not None
        assert len(doc.chapters) == 2
        assert doc.chapters[0].title == "Introduction"
        assert doc.chapters[1].title == "Chapter 1"
    finally:
        path.unlink()


def test_load_txt_mixed_patterns():
    """TXT with chapter pattern headings detects chapters."""
    content = "Chapter 1\nIntroduction text here.\n\nChapter 2\nMore text here.\n"
    path = _write_tmp(content)
    try:
        doc = load_txt(path, "hash_pat", "book.txt")
        assert doc is not None
        assert len(doc.chapters) >= 2
    finally:
        path.unlink()


def test_load_txt_empty_file():
    """Empty TXT file returns None."""
    path = _write_tmp("   \n\n  ")
    try:
        doc = load_txt(path, "empty_hash")
        assert doc is None
    finally:
        path.unlink()


def test_load_txt_encoding_fallback():
    """TXT file with latin-1 encoding loads successfully via fallback."""
    content = "Caf\xe9 au lait is a popular drink."  # \xe9 = é in latin-1
    path = _write_tmp(content, encoding="latin-1")
    try:
        doc = load_txt(path, "latin_hash", "cafe.txt")
        assert doc is not None
        assert len(doc.chapters) >= 1
    finally:
        path.unlink()


# ---------------------------------------------------------------------------
# preview_txt
# ---------------------------------------------------------------------------


def test_preview_txt():
    """Preview returns ChapterPreview objects with correct count and titles."""
    content = "# Intro\nIntro text.\n\n# Chapter 1\nChapter one text.\n"
    path = _write_tmp(content)
    try:
        doc, previews = preview_txt(path, "prev_hash")
        assert doc is not None
        assert len(previews) == 2
        assert previews[0].title == "Intro"
        assert previews[0].index == 0
        assert previews[1].title == "Chapter 1"
        assert doc.chapters == []
    finally:
        path.unlink()


def test_preview_txt_empty():
    """Preview of empty file returns (None, [])."""
    path = _write_tmp("")
    try:
        doc, previews = preview_txt(path, "empty_prev")
        assert doc is None
        assert previews == []
    finally:
        path.unlink()
