import logging
import re

logger = logging.getLogger(__name__)


def normalize(pages_text: list[str]) -> list[str]:
    """
    Normalize a list of page texts.

    - Collapse runs of spaces/tabs to a single space
    - Unify line endings
    - Strip repeated header/footer lines (appearing in >30% of pages)
    - Mark page boundaries with ---PAGE--- sentinel (handled by caller)
    """
    if not pages_text:
        return pages_text

    cleaned = [_clean_whitespace(t) for t in pages_text]
    cleaned = _strip_repeated_lines(cleaned)
    logger.debug("Normalized %d pages", len(cleaned))
    return cleaned


def _clean_whitespace(text: str) -> str:
    # Unify line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Remove trailing spaces on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def _strip_repeated_lines(pages: list[str]) -> list[str]:
    """Remove lines that appear in >30% of pages (likely headers/footers)."""
    threshold = max(2, int(len(pages) * 0.3))

    # Count line occurrences across all pages
    line_counts: dict[str, int] = {}
    for page_text in pages:
        # Only examine first and last 3 lines (header/footer zone)
        lines = page_text.split("\n")
        candidates = set(lines[:3] + lines[-3:])
        for line in candidates:
            stripped = line.strip()
            if stripped:
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

    repeated = {line for line, count in line_counts.items() if count >= threshold}
    if not repeated:
        return pages

    logger.debug("Stripping %d repeated header/footer lines", len(repeated))
    result = []
    for page_text in pages:
        lines = page_text.split("\n")
        filtered = [ln for ln in lines if ln.strip() not in repeated]
        result.append("\n".join(filtered).strip())
    return result
