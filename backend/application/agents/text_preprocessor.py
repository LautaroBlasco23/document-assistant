"""Text pre-processor for the improve formatting feature.

Pre-processes document text before sending to the LLM:
  1. Removes exact duplicate paragraphs (non-consecutive)
  2. Detects potential titles/headings and wraps them in structural markers

The markers (__HEADING__, __SUBHEADING__) give the LLM explicit structural hints
it currently lacks when receiving a flat wall of text.
"""

import re


def remove_duplicate_paragraphs(text: str) -> str:
    """Remove exact duplicate paragraphs that appear multiple times.

    Keeps the first occurrence of each unique paragraph.  Duplicates are
    identified after normalising whitespace and case (stripped + lowered).

    Image references (paragraphs starting with '![') are always kept since
    duplicate image refs are usually intentional layout, not extraction
    artefacts.
    """
    if not text.strip():
        return text

    paragraphs = text.split("\n\n")
    seen: set[str] = set()
    result: list[str] = []

    for para in paragraphs:
        # Always keep image references — duplicate images are layout, not artefacts
        if para.lstrip().startswith("!["):
            result.append(para)
            continue

        key = " ".join(para.split()).lower()  # normalised
        if key not in seen:
            seen.add(key)
            result.append(para)

    return "\n\n".join(result)


# ---------------------------------------------------------------------------
# Title / heading detection
# ---------------------------------------------------------------------------

_QUOTE_CHARS = frozenset([
    '\u201c', '\u201d', '\u2018', '\u2019',  # curly double and single quotes
    '\u300c', '\u300d',  # Japanese corner brackets
    '\u201f',  # double high-reversed-9 quotation mark
    '"', "'",  # straight quotes
])
_LIST_PREFIXES = ("-", "*", "•", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "0.")
_SENTENCE_ENDERS = re.compile(r"[.!?…;:]$")
_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
_WORD_RE = re.compile(r"\w+")


def _is_title_case(words: list[str]) -> bool:
    """Return True if the majority of words follow title-case rules."""
    # Filter out short words that are often lowercased (of, the, a, ...)
    _short = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
              "for", "of", "with", "by", "from", "is", "it", "as", "no", "not"}
    significant = [w for w in words if w.lower() not in _short and len(w) > 1]
    if not significant:
        return False
    title_cased = sum(1 for w in significant if w[0].isupper() and w[1:].islower())
    return title_cased / len(significant) >= 0.8


def _is_all_caps(words: list[str]) -> bool:
    """Return True if the majority of words are ALL CAPS."""
    if not words:
        return False
    caps = sum(1 for w in words if len(w) > 1 and w.isupper())
    return caps / len(words) >= 0.7


def _looks_like_title(text: str) -> tuple[bool, bool]:
    """Heuristically determine whether *text* is a heading or subheading.

    Returns (is_heading, is_subheading).
    """
    stripped = text.strip()
    if not stripped:
        return False, False

    # Reject paragraphs that contain image refs as the whole content
    if stripped.startswith("!["):
        return False, False

    # Reject list items
    if any(stripped.startswith(pfx) for pfx in _LIST_PREFIXES):
        return False, False

    # Reject dialogue
    if stripped[0] in _QUOTE_CHARS:
        return False, False

    words = _WORD_RE.findall(stripped)
    word_count = len(words)

    # Heading: 1–8 words, not a sentence, title-case or all-caps
    if 1 <= word_count <= 8:
        # Reject if it ends with sentence-ending punctuation (it's a sentence, not a title)
        if _SENTENCE_ENDERS.search(stripped):
            return False, False
        # Reject if it contains a comma (likely a sentence fragment)
        if "," in stripped:
            return False, False
        if _is_title_case(words) or _is_all_caps(words):
            return True, False

    # Subheading: 9–15 words, same criteria
    if 9 <= word_count <= 15:
        if _SENTENCE_ENDERS.search(stripped):
            return False, False
        if "," in stripped:
            return False, False
        if _is_title_case(words) or _is_all_caps(words):
            return False, True

    return False, False


def detect_and_mark_titles(text: str) -> str:
    """Wrap potential headings and subheadings with structural markers.

    Markers:
      __HEADING__...__END_HEADING__     → ## Heading
      __SUBHEADING__...__END_SUBHEADING__ → ### Subheading

    These are consumed by the LLM (prompt tells it to convert) and by
    ``_clean_residual_markers`` in the service layer as a safety net.
    """
    if not text.strip():
        return text

    paragraphs = text.split("\n\n")
    result: list[str] = []

    for para in paragraphs:
        is_heading, is_subheading = _looks_like_title(para)
        if is_heading:
            result.append(f"__HEADING__{para.strip()}__END_HEADING__")
        elif is_subheading:
            result.append(f"__SUBHEADING__{para.strip()}__END_SUBHEADING__")
        else:
            result.append(para)

    return "\n\n".join(result)


def preprocess_for_improvement(text: str) -> str:
    """Full pre-processing pipeline for the improve formatting feature.

    Steps:
      1. Remove exact duplicate paragraphs (non-consecutive)
      2. Detect and mark potential titles/headings

    Returns text ready for the LLM.
    """
    if not text.strip():
        return text
    text = remove_duplicate_paragraphs(text)
    text = detect_and_mark_titles(text)
    return text
