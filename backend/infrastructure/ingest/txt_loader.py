import logging
import re
from pathlib import Path

from core.model.document import Chapter, Document, Page, Section
from infrastructure.ingest.normalizer import normalize
from infrastructure.ingest.pdf_loader import (
    _CHAPTER_PATTERNS,
    ChapterPreview,
)

logger = logging.getLogger(__name__)

_MARKDOWN_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MARKDOWN_H2 = re.compile(r"^#{2,3}\s+(.+)$", re.MULTILINE)

_SEPARATOR_PATTERN = re.compile(r"^#{3,}\s*$", re.MULTILINE)
_CHAPTER_TITLE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

_SYNTHETIC_WORDS_PER_CHAPTER = 5000


def build_document_from_text(
    title: str,
    content: str,
    file_hash: str,
    original_filename: str = "",
) -> Document:
    """Build a Document from raw text, detecting chapter boundaries.

    Detection priority:
    1. ### separator format (### + # Title + ###)
    2. Markdown level-1 headers (# Title)
    3. Common heading patterns (reused from pdf_loader._CHAPTER_PATTERNS)
    4. Synthetic fallback (~5000 words per chapter)
    """
    if not content.strip():
        return Document(
            source_path="<custom>" if not original_filename else original_filename,
            title=title,
            file_hash=file_hash,
            original_filename=original_filename,
            chapters=[],
        )

    chapters = (
        _detect_separator_chapters(content)
        or _detect_markdown_chapters(content)
        or _detect_pattern_chapters(content)
        or _synthetic_chapters(content)
    )

    source_path = "<custom>" if not original_filename else original_filename

    return Document(
        source_path=source_path,
        title=title,
        file_hash=file_hash,
        original_filename=original_filename,
        chapters=chapters,
    )


def load_txt(path: Path, file_hash: str, original_filename: str = "") -> Document | None:
    """Load a TXT file and return a Document, or None if empty."""
    display_name = original_filename or path.name
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed for %s, falling back to latin-1", display_name)
        text = path.read_text(encoding="latin-1")

    if not text.strip():
        logger.warning("Empty TXT file: %s", display_name)
        return None

    title = Path(display_name).stem
    doc = build_document_from_text(title, text, file_hash, display_name)
    doc.source_path = str(path)

    logger.info("Loaded TXT %s: %d chapters", display_name, len(doc.chapters))
    return doc


def preview_txt(path: Path, file_hash: str) -> tuple[Document | None, list[ChapterPreview]]:
    """Preview a TXT file's chapter structure without loading full text.

    Returns (doc, chapters) where doc has empty chapter pages.
    """
    display_name = path.name
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")

    if not text.strip():
        return None, []

    title = Path(display_name).stem

    chapters = (
        _detect_separator_chapters(text)
        or _detect_markdown_chapters(text)
        or _detect_pattern_chapters(text)
        or _synthetic_chapters(text)
    )

    previews = [
        ChapterPreview(
            index=ch.index,
            title=ch.title,
            page_start=1,
            page_end=1,
        )
        for ch in chapters
    ]

    result_doc = Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=display_name,
        chapters=[],
    )

    return result_doc, previews


def _detect_markdown_chapters(content: str) -> list[Chapter]:
    """Split content on # (level-1) markdown headers. ## / ### become Sections."""
    h1_positions = [(m.start(), m.group(1).strip()) for m in _MARKDOWN_H1.finditer(content)]
    if not h1_positions:
        return []

    chapters: list[Chapter] = []
    for i, (pos, h1_title) in enumerate(h1_positions):
        end = h1_positions[i + 1][0] if i + 1 < len(h1_positions) else len(content)
        chapter_text = content[pos:end]

        normalized = normalize([chapter_text])
        clean_text = normalized[0] if normalized else chapter_text

        sections = _extract_subsections(chapter_text)

        page = Page(number=1, text=clean_text)
        chapters.append(
            Chapter(
                index=i,
                title=h1_title,
                pages=[page],
                sections=sections,
            )
        )

    if len(chapters) >= 1:
        return chapters
    return []


def _extract_subsections(text: str) -> list[Section]:
    """Extract ## / ### headers as Section objects from a chapter block of text."""
    sections = []
    for m in _MARKDOWN_H2.finditer(text):
        sections.append(Section(title=m.group(1).strip(), page_start=1, page_end=1))
    return sections


def _detect_separator_chapters(content: str) -> list[Chapter]:
    """Split content on ### separator format: ### followed by # Title followed by ###."""
    matches = list(_SEPARATOR_PATTERN.finditer(content))
    if len(matches) < 2:
        return []

    chapters: list[Chapter] = []
    for i in range(len(matches) - 1):
        start_pos = matches[i].end()
        end_pos = matches[i + 1].start()

        chapter_block = content[start_pos:end_pos].strip()

        title_match = _CHAPTER_TITLE.search(chapter_block)
        if not title_match:
            continue

        title = title_match.group(1).strip()

        title_end = title_match.end()
        chapter_text = chapter_block[title_end:].strip()

        normalized = normalize([chapter_text])
        clean_text = normalized[0] if normalized else chapter_text

        page = Page(number=1, text=clean_text)
        sections = _extract_subsections(chapter_text)

        chapters.append(
            Chapter(
                index=len(chapters),
                title=title,
                pages=[page],
                sections=sections,
            )
        )

    return chapters


def _detect_pattern_chapters(content: str) -> list[Chapter]:
    """Split content into chapters using PDF-style heading patterns."""
    paragraphs = re.split(r"\n{2,}", content)

    chapter_breaks: list[tuple[int, str]] = []
    char_pos = 0
    for para in paragraphs:
        stripped = para.strip()
        if stripped:
            first_line = stripped.split("\n")[0].strip()
            if first_line and any(p.match(first_line) for p in _CHAPTER_PATTERNS):
                chapter_breaks.append((char_pos, first_line))
        char_pos += len(para) + 2

    if len(chapter_breaks) < 2:
        return []

    chapters: list[Chapter] = []
    for i, (pos, ch_title) in enumerate(chapter_breaks):
        end = chapter_breaks[i + 1][0] if i + 1 < len(chapter_breaks) else len(content)
        chapter_text = content[pos:end]

        normalized = normalize([chapter_text])
        clean_text = normalized[0] if normalized else chapter_text

        page = Page(number=1, text=clean_text)
        chapters.append(
            Chapter(
                index=i,
                title=ch_title,
                pages=[page],
            )
        )

    return chapters


def _synthetic_chapters(content: str) -> list[Chapter]:
    """Split content into synthetic chapters of ~5000 words each."""
    words = content.split()
    if not words:
        return [Chapter(index=0, title="Document", pages=[])]

    chapters: list[Chapter] = []
    for i in range(0, len(words), _SYNTHETIC_WORDS_PER_CHAPTER):
        chunk_words = words[i : i + _SYNTHETIC_WORDS_PER_CHAPTER]
        chunk_text = " ".join(chunk_words)
        normalized = normalize([chunk_text])
        clean_text = normalized[0] if normalized else chunk_text
        page = Page(number=1, text=clean_text)
        chapters.append(
            Chapter(
                index=len(chapters),
                title=f"Section {len(chapters) + 1}",
                pages=[page],
            )
        )

    return chapters or [
        Chapter(
            index=0,
            title="Document",
            pages=[Page(number=1, text=content)],
        )
    ]
