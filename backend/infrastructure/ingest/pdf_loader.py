import logging
import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTAnno, LTChar, LTTextContainer

from core.model.document import Chapter, Document, Page, Section
from infrastructure.ingest.normalizer import clean_text, normalize

logger = logging.getLogger(__name__)

# Pages averaging fewer non-whitespace chars than this trigger the pdfminer fallback.
_SPARSE_CHARS_PER_PAGE = 50

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
# Ordered by specificity - more specific patterns should come first
_CHAPTER_PATTERNS = [
    # Chapter + number (with optional colon and title): "Chapter 1",
    # "Chapter 1: Introduction", "CHAPTER 2"
    re.compile(r"^chapter\s+\d+(?::?\s+.+)?$", re.IGNORECASE),
    # Chapter + written ordinal: "Chapter One", "Chapter Twenty-One"
    re.compile(r"^chapter\s+(?:" + _ORDINAL_WORDS + r")(?::?\s+.+)?$", re.IGNORECASE),
    # Numbered chapter with title: "1. Introduction", "1.2 Introduction", "12. CHAPTER TITLE"
    re.compile(r"^\d+(?:\.\d+)*\.?\s*[A-Z].*", re.IGNORECASE),
    # Number + space + uppercase title: "1 Introduction", "10 Methods and Materials"
    re.compile(r"^\d+\s+[A-Z][A-Za-z]"),
    # Part with Roman numerals or numbers: "Part I", "Part 1", "Part III: Summary"
    re.compile(r"^part\s+[IVX\d]+(?::?\s+.*)?$", re.IGNORECASE),
    # Section marker: "Section 1", "SECTION 2"
    re.compile(r"^section\s+\d+", re.IGNORECASE),
    # Standalone uppercase short line (likely a chapter/section title): "PREFACE", "REFERENCES"
    re.compile(
        r"^(?:CHAPTER|SECTION|PART|PROLOGUE|EPILOGUE|FOREWORD|AFTERWORD|APPENDIX|PREFACE|REFERENCES|INTRODUCTION|CONCLUSION)(?:\s*$|\s+\n)"
    ),
    # Single "1" or "01" at start of page (with optional content after newline)
    re.compile(r"^\s*\d{1,3}\s*\n\n"),
]

SYNTHETIC_CHAPTER_SIZE = 20  # pages per synthetic chapter when no headings found


@dataclass
class ChapterPreview:
    """Lightweight chapter metadata without full page text."""

    index: int
    title: str
    page_start: int  # 1-based
    page_end: int  # 1-based


def preview_pdf(path: Path, file_hash: str) -> tuple[Document | None, list[ChapterPreview]]:
    """Extract chapter structure from a PDF without loading full page text.

    This is a lightweight operation that only reads the table of contents
    and uses heuristics to determine chapter boundaries.

    Returns (doc, chapters) where doc has no populated chapters (just metadata).
    chapters is the list of ChapterPreview objects.
    """
    doc = fitz.open(str(path))
    title = doc.metadata.get("title") or path.stem
    author = doc.metadata.get("author", "")
    total_pages = len(doc)

    chapters = _extract_chapter_structure(doc, total_pages)
    doc.close()

    result_doc = Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=path.name,
        chapters=[],  # Not populated - use full load for that
        metadata={"author": author},
    )

    logger.info("Preview PDF %s: %d pages, %d chapters", path.name, total_pages, len(chapters))
    return result_doc, chapters


def _extract_chapter_structure(doc: fitz.Document, total_pages: int) -> list[ChapterPreview]:
    """Extract chapter structure from ToC or heuristics without loading page text."""
    toc = doc.get_toc()
    if not toc:
        return _synthetic_chapter_structure(total_pages)

    level1 = [(title, page_num) for level, title, page_num in toc if level == 1]
    level2 = [(title, page_num) for level, title, page_num in toc if level == 2]

    if not level1 and not level2:
        return _synthetic_chapter_structure(total_pages)

    if not level1 and level2:
        return [ChapterPreview(index=0, title="Document", page_start=1, page_end=total_pages)]

    chapters: list[ChapterPreview] = []
    all_entries = [(level, title, page_num) for level, title, page_num in toc if level in (1, 2)]

    chapter_index = 0
    for i, (entry_level, entry_title, entry_page) in enumerate(all_entries):
        if entry_level != 1:
            continue

        chapter_end_page = total_pages
        for j in range(i + 1, len(all_entries)):
            if all_entries[j][0] == 1:
                chapter_end_page = all_entries[j][2] - 1
                break

        chapters.append(
            ChapterPreview(
                index=chapter_index,
                title=entry_title or f"Chapter {chapter_index + 1}",
                page_start=entry_page,
                page_end=chapter_end_page,
            )
        )
        chapter_index += 1

    return chapters or _synthetic_chapter_structure(total_pages)


def _synthetic_chapter_structure(total_pages: int) -> list[ChapterPreview]:
    """Generate synthetic chapter structure based on page ranges."""
    chapters = []
    for i in range(0, total_pages, SYNTHETIC_CHAPTER_SIZE):
        end_page = min(i + SYNTHETIC_CHAPTER_SIZE, total_pages)
        chapters.append(
            ChapterPreview(
                index=len(chapters),
                title=f"Section {len(chapters) + 1}",
                page_start=i + 1,
                page_end=end_page,
            )
        )
    return chapters or [
        ChapterPreview(index=0, title="Document", page_start=1, page_end=total_pages)
    ]


def _nonws_chars(pages: list[str]) -> int:
    """Count total non-whitespace characters across all pages."""
    return sum(len(p.replace(" ", "").replace("\n", "").replace("\t", "")) for p in pages)


def _avg_nonws_per_page(pages: list[str]) -> float:
    if not pages:
        return 0.0
    return _nonws_chars(pages) / len(pages)


def _is_sparse(pages: list[str], threshold: int = _SPARSE_CHARS_PER_PAGE) -> bool:
    """Return True if average non-whitespace chars per page is below threshold."""
    return _avg_nonws_per_page(pages) < threshold


def _sample(pages: list[str], max_chars: int = 120) -> str:
    """Return the first max_chars of non-empty content across pages."""
    for p in pages:
        stripped = p.strip()
        if stripped:
            return repr(stripped[:max_chars])
    return "(empty)"


def _extract_pages_pymupdf(doc: fitz.Document) -> list[str]:
    """Extract per-page text using PyMuPDF default text mode."""
    return [page.get_text() for page in doc]


def _extract_pages_pymupdf_blocks(doc: fitz.Document) -> list[str]:
    """Extract per-page text using PyMuPDF blocks mode.

    Uses a different internal layout pass than the default text mode —
    sometimes recovers text that the default mode misses.
    """
    pages = []
    for page in doc:
        blocks = page.get_text("blocks")  # list of (x0,y0,x1,y1,text,block_no,block_type)
        text = "\n".join(b[4] for b in sorted(blocks, key=lambda b: (b[1], b[0])) if b[6] == 0)
        pages.append(text)
    return pages


def _extract_pages_pdfminer(path: Path) -> list[str]:
    """Extract per-page text using pdfminer.six.

    Handles PDFs where PyMuPDF fails due to missing ToUnicode CMap or
    non-standard font encodings. Iterates over layout elements directly
    to capture all LTChar/LTAnno objects in reading order.
    """
    pages: list[str] = []
    for page_layout in extract_pages(str(path)):
        buf: list[str] = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    for char in text_line:
                        if isinstance(char, LTChar):
                            buf.append(char.get_text())
                        elif isinstance(char, LTAnno):
                            buf.append(char.get_text())
        pages.append("".join(buf))
    return pages


def _best_extraction(
    candidates: list[tuple[str, list[str]]],
    display_name: str,
) -> list[str]:
    """Run each extractor in order; return the first non-sparse result.

    candidates: list of (label, pages) already extracted.
    Logs a per-extractor summary to make failures easy to diagnose.
    """
    best_label, best_pages = candidates[0]
    best_avg = _avg_nonws_per_page(best_pages)

    for label, pages in candidates:
        avg = _avg_nonws_per_page(pages)
        logger.info(
            "[%s] %s — %d page(s), %.0f non-ws chars/page, sample: %s",
            label,
            display_name,
            len(pages),
            avg,
            _sample(pages),
        )
        if avg > best_avg:
            best_avg = avg
            best_label = label
            best_pages = pages
        if not _is_sparse(pages):
            logger.info("Using extractor '%s' for %s", label, display_name)
            return pages

    logger.warning(
        "All extractors sparse for %s — best was '%s' (%.0f non-ws chars/page). "
        "File may be image-based, encrypted, or use unsupported fonts.",
        display_name,
        best_label,
        best_avg,
    )
    return best_pages


def load_pdf(path: Path, file_hash: str, original_filename: str = "") -> Document:
    """Extract a Document from a PDF file.

    Tries three extraction strategies in order, picking the first that
    yields enough text:
      1. PyMuPDF default  (fast, works for most PDFs)
      2. PyMuPDF blocks   (different layout pass, sometimes recovers missed text)
      3. pdfminer.six     (independent parser, best for CID/encoding edge cases)
    """
    doc = fitz.open(str(path))
    display_name = original_filename or path.name
    title = doc.metadata.get("title") or Path(display_name).stem
    author = doc.metadata.get("author", "")

    pymupdf_pages = _extract_pages_pymupdf(doc)

    if _is_sparse(pymupdf_pages):
        blocks_pages = _extract_pages_pymupdf_blocks(doc)
        pdfminer_pages = _extract_pages_pdfminer(path)
        raw_pages = _best_extraction(
            [
                ("pymupdf-text", pymupdf_pages),
                ("pymupdf-blocks", blocks_pages),
                ("pdfminer", pdfminer_pages),
            ],
            display_name,
        )
    else:
        logger.info(
            "pymupdf-text extracted %s: %d page(s), %.0f non-ws chars/page",
            display_name,
            len(pymupdf_pages),
            _avg_nonws_per_page(pymupdf_pages),
        )
        raw_pages = pymupdf_pages

    normalized = normalize(raw_pages)

    # Convert to Page objects for chapter detection
    pages = [Page(number=i + 1, text=text) for i, text in enumerate(normalized)]

    # Detect chapters BEFORE cross-page reflow to preserve page boundaries accurately
    chapters = (
        _detect_chapters_from_toc(doc, pages)
        or _detect_chapters(pages)
        or _synthetic_chapters(pages)
    )

    # Now apply text normalization to each chapter's content
    for chapter in chapters:
        cleaned_pages = []
        for page in chapter.pages:
            cleaned_text = clean_text(page.text, dehyphenate=False)
            cleaned_pages.append(Page(number=page.number, text=cleaned_text))
        chapter.pages = cleaned_pages

    doc.close()

    logger.info(
        "Loaded PDF %s: %d pages, %d chapters", display_name, len(normalized), len(chapters)
    )

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

    # Return chapters if we found at least 2, or if we found exactly 1
    # (single-chapter documents should use "Document" as title, not "Introduction")
    if len(chapters) >= 2:
        return chapters
    if len(chapters) == 1:
        # Single chapter detected - rename to "Document" for articles/short docs
        chapters[0] = Chapter(
            index=0,
            title="Document",
            pages=chapters[0].pages,
            sections=chapters[0].sections,
        )
        return chapters
    return []


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
