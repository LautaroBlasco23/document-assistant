import logging
import re
from pathlib import Path

import fitz  # PyMuPDF

from core.model.document import Chapter, Document, Page
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

    raw_pages: list[str] = []
    for page in doc:
        raw_pages.append(page.get_text())
    doc.close()

    normalized = normalize(raw_pages)

    pages = [
        Page(number=i + 1, text=text)
        for i, text in enumerate(normalized)
    ]

    chapters = _detect_chapters(pages) or _synthetic_chapters(pages)
    logger.info("Loaded PDF %s: %d pages, %d chapters", display_name, len(pages), len(chapters))

    return Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=original_filename or path.name,
        chapters=chapters,
        metadata={"author": doc.metadata.get("author", "") if not doc.is_closed else ""},
    )


def _is_chapter_heading(text: str) -> bool:
    first_line = text.strip().split("\n")[0].strip()
    return any(p.match(first_line) for p in _CHAPTER_PATTERNS)


def _detect_chapters(pages: list[Page]) -> list[Chapter]:
    """Split pages into chapters based on heading patterns."""
    chapters: list[Chapter] = []
    current_pages: list[Page] = []
    current_title = "Introduction"
    chapter_index = 0

    for page in pages:
        if _is_chapter_heading(page.text) and current_pages:
            chapters.append(Chapter(index=chapter_index, title=current_title, pages=current_pages))
            chapter_index += 1
            current_title = page.text.strip().split("\n")[0].strip()
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
