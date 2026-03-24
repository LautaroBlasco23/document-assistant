import logging
from pathlib import Path

from core.model.chunk import Chunk
from core.model.document import Document

logger = logging.getLogger(__name__)


def _output_dir(doc: Document, base: Path) -> Path:
    safe_title = _safe_name(doc.title)
    d = base / safe_title
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_summary(
    doc: Document,
    chapter_index: int,
    summary: str | dict,
    chunks: list[Chunk],
    output_dir: Path,
) -> Path:
    chapter = _get_chapter(doc, chapter_index)
    title = chapter.title if chapter else f"Chapter {chapter_index}"
    pages = _page_range(chunks)

    out = _output_dir(doc, output_dir) / f"chapter{chapter_index + 1}-summary.md"
    with open(out, "w") as f:
        f.write(f"# Chapter {chapter_index + 1} — {title}\n\n")
        f.write(f"**Source:** {Path(doc.source_path).name} (pages {pages})\n\n")
        if isinstance(summary, dict):
            description = summary.get("description", "")
            bullets = summary.get("bullets", [])
            if description:
                f.write("## Overview\n\n")
                f.write(description + "\n\n")
            if bullets:
                f.write("## Key Takeaways\n\n")
                for b in bullets:
                    f.write(f"- {b}\n")
                f.write("\n")
        else:
            f.write(summary.strip() + "\n\n")
        if chunks:
            f.write("## References\n\n")
            for c in chunks[:5]:
                page = c.metadata.page_number if c.metadata else "?"
                quote = c.text[:120].replace("\n", " ")
                f.write(f'- p.{page}: "{quote}..."\n')

    logger.info("Wrote summary: %s", out)
    return out


def write_flashcards(
    doc: Document,
    chapter_index: int,
    cards: list[dict],
    output_dir: Path,
) -> Path:
    chapter = _get_chapter(doc, chapter_index)
    title = chapter.title if chapter else f"Chapter {chapter_index}"

    out = _output_dir(doc, output_dir) / f"chapter{chapter_index + 1}-flashcards.md"
    with open(out, "w") as f:
        f.write(f"# Chapter {chapter_index + 1} — {title}: Flashcards\n\n")
        for card in cards:
            front = card.get("front", "").strip()
            back = card.get("back", "").strip()
            if front and back:
                f.write(f"**Front:** {front}\n\n")
                f.write(f"**Back:** {back}\n\n")
                f.write("---\n\n")

    logger.info("Wrote flashcards: %s", out)
    return out


def _get_chapter(doc: Document, index: int):
    for ch in doc.chapters:
        if ch.index == index:
            return ch
    return None


def _page_range(chunks: list[Chunk]) -> str:
    pages = [c.metadata.page_number for c in chunks if c.metadata and c.metadata.page_number]
    if not pages:
        return "?"
    return f"{min(pages)}–{max(pages)}"


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()
