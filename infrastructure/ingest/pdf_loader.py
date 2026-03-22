import logging
import re
from pathlib import Path

import fitz  # PyMuPDF

from core.model.document import Chapter, Document, Page, Section
from infrastructure.ingest.normalizer import normalize

logger = logging.getLogger(__name__)

# Written-out ordinals for chapter headings (ONE through FIFTY, with compound forms)
_ORDINAL_WORDS = (
    "ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|"
    "ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|"
    "TWENTY[- ]ONE|TWENTY[- ]TWO|TWENTY[- ]THREE|TWENTY[- ]FOUR|TWENTY[- ]FIVE|"
    "TWENTY[- ]SIX|TWENTY[- ]SEVEN|TWENTY[- ]EIGHT|TWENTY[- ]NINE|THIRTY|"
    "THIRTY[- ]ONE|THIRTY[- ]TWO|THIRTY[- ]THREE|THIRTY[- ]FOUR|THIRTY[- ]FIVE|"
    "THIRTY[- ]SIX|THIRTY[- ]SEVEN|THIRTY[- ]EIGHT|THIRTY[- ]NINE|FORTY|"
    "FORTY[- ]ONE|FORTY[- ]TWO|FORTY[- ]THREE|FORTY[- ]FOUR|FORTY[- ]FIVE|"
    "FORTY[- ]SIX|FORTY[- ]SEVEN|FORTY[- ]EIGHT|FORTY[- ]NINE|FIFTY"
)

# Patterns that signal a chapter heading
_CHAPTER_PATTERNS = [
    re.compile(r"^chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^chapter\s+(?:" + _ORDINAL_WORDS + r")\b", re.IGNORECASE),
    re.compile(r"^\d+\.\s+[A-Z]"),
    re.compile(r"^part\s+[IVX\d]+", re.IGNORECASE),
]

SYNTHETIC_CHAPTER_SIZE = 20  # pages per synthetic chapter when no headings found


def load_pdf(path: Path, file_hash: str, original_filename: str = "") -> Document:
    """Extract a Document from a PDF file using PyMuPDF."""
    doc = fitz.open(str(path))
    display_name = original_filename or path.name
    title = doc.metadata.get("title") or Path(display_name).stem
    author = doc.metadata.get("author", "")

    raw_pages: list[str] = []
    for page in doc:
        raw_pages.append(page.get_text())

    normalized = normalize(raw_pages)

    pages = [
        Page(number=i + 1, text=text)
        for i, text in enumerate(normalized)
    ]

    # Try ToC-based detection first, then heuristic, then synthetic
    chapters = (
        _detect_chapters_from_toc(doc, pages)
        or _detect_chapters(pages)
        or _synthetic_chapters(pages)
    )
    doc.close()

    logger.info("Loaded PDF %s: %d pages, %d chapters", display_name, len(pages), len(chapters))

    return Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=original_filename or path.name,
        chapters=chapters,
        metadata={"author": author},
    )


def _detect_chapters_from_toc(doc: fitz.Document, pages: list[Page]) -> list[Chapter]:
    """Build chapter/section hierarchy from PDF outline (table of contents).

    PyMuPDF's get_toc() returns entries as [level, title, page_number] where
    page_number is 1-based. Level-1 entries become chapters; level-2 entries
    become sections nested under the preceding level-1 chapter.

    If no level-1 entries exist but level-2 entries do, creates one synthetic
    chapter "Document" containing all level-2 entries as sections.

    Returns an empty list if the PDF has no ToC (triggers heuristic fallback).
    """
    toc = doc.get_toc()
    if not toc:
        return []

    total_pages = len(pages)

    # Separate by level
    level1 = [(title, page_num) for level, title, page_num in toc if level == 1]
    level2 = [(title, page_num) for level, title, page_num in toc if level == 2]

    if not level1 and not level2:
        return []

    def _pages_slice(start_1based: int, end_1based: int) -> list[Page]:
        """Return pages from start_1based to end_1based (inclusive, 1-based)."""
        start_idx = max(0, start_1based - 1)
        end_idx = min(total_pages, end_1based)
        return pages[start_idx:end_idx]

    # Case: only level-2 entries — wrap all in one synthetic "Document" chapter
    if not level1 and level2:
        sections: list[Section] = []
        for i, (sec_title, sec_page) in enumerate(level2):
            next_page = level2[i + 1][1] - 1 if i + 1 < len(level2) else total_pages
            sections.append(Section(title=sec_title, page_start=sec_page, page_end=next_page))
        chapter_pages = _pages_slice(1, total_pages)
        return [Chapter(index=0, title="Document", pages=chapter_pages, sections=sections)]

    # Build chapters from level-1 entries and nest level-2 as sections
    chapters: list[Chapter] = []
    chapter_index = 0

    # Build a flat list combining level-1 (chapters) and level-2 (sections)
    # with type tags to process in order
    all_entries = [(level, title, page_num) for level, title, page_num in toc if level in (1, 2)]

    i = 0
    while i < len(all_entries):
        entry_level, entry_title, entry_page = all_entries[i]
        if entry_level != 1:
            i += 1
            continue

        # Determine end page for this chapter (start of next level-1 entry or end of doc)
        chapter_end_page = total_pages
        for j in range(i + 1, len(all_entries)):
            if all_entries[j][0] == 1:
                chapter_end_page = all_entries[j][2] - 1
                break

        # Collect level-2 entries that belong to this chapter
        chapter_sections: list[Section] = []
        j = i + 1
        while j < len(all_entries) and all_entries[j][0] != 1:
            sec_level, sec_title, sec_page = all_entries[j]
            if sec_level == 2:
                # Section ends at the start of the next sibling section (level 2) or chapter end
                sec_end_page = chapter_end_page
                for k in range(j + 1, len(all_entries)):
                    if all_entries[k][0] == 1:
                        break
                    if all_entries[k][0] == 2:
                        sec_end_page = all_entries[k][2] - 1
                        break
                chapter_sections.append(
                    Section(title=sec_title, page_start=sec_page, page_end=sec_end_page)
                )
            j += 1

        chapter_pages = _pages_slice(entry_page, chapter_end_page)
        chapters.append(
            Chapter(
                index=chapter_index,
                title=entry_title,
                pages=chapter_pages,
                sections=chapter_sections,
            )
        )
        chapter_index += 1
        i += 1

    return chapters if chapters else []


def _is_chapter_heading(text: str) -> tuple[bool, int]:
    """Check if any of the first 5 lines is a chapter heading.

    Returns (is_heading, line_index) where line_index is the index of
    the matching line (0-based). Returns (False, -1) if no match found.
    """
    lines = text.strip().split("\n")
    for i, line in enumerate(lines[:5]):
        stripped = line.strip()
        if stripped and any(p.match(stripped) for p in _CHAPTER_PATTERNS):
            return True, i
    return False, -1


def _detect_chapters(pages: list[Page]) -> list[Chapter]:
    """Split pages into chapters based on heading patterns."""
    chapters: list[Chapter] = []
    current_pages: list[Page] = []
    current_title = "Introduction"
    chapter_index = 0

    for page in pages:
        is_heading, line_idx = _is_chapter_heading(page.text)
        if is_heading and current_pages:
            chapters.append(Chapter(index=chapter_index, title=current_title, pages=current_pages))
            chapter_index += 1
            # Extract the actual heading line as the chapter title
            lines = page.text.strip().split("\n")
            current_title = lines[line_idx].strip()
            current_pages = [page]
        else:
            current_pages.append(page)

    if current_pages:
        chapters.append(Chapter(index=chapter_index, title=current_title, pages=current_pages))

    # Only return if we found at least 2 chapters (otherwise fall back to synthetic)
    return chapters if len(chapters) >= 2 else []


def _synthetic_chapters(pages: list[Page]) -> list[Chapter]:
    """Group pages into fixed-size chapters when no headings are detected."""
    chapters = []
    for i in range(0, len(pages), SYNTHETIC_CHAPTER_SIZE):
        chunk_pages = pages[i : i + SYNTHETIC_CHAPTER_SIZE]
        chapters.append(
            Chapter(
                index=len(chapters),
                title=f"Section {len(chapters) + 1}",
                pages=chunk_pages,
            )
        )
    return chapters or [Chapter(index=0, title="Document", pages=pages)]
