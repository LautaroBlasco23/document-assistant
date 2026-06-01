"""
Unit tests for text pre-processor.

Subject: application/agents/text_preprocessor.py
Scope:   remove_duplicate_paragraphs, detect_and_mark_titles, preprocess_for_improvement
"""

from application.agents.text_preprocessor import (
    detect_and_mark_titles,
    preprocess_for_improvement,
    remove_duplicate_paragraphs,
)

# ---------------------------------------------------------------------------
# remove_duplicate_paragraphs
# ---------------------------------------------------------------------------


def test_remove_duplicate_paragraphs_removes_non_consecutive_dupes():
    """Non-consecutive exact duplicate paragraphs must be removed (keep first occurrence)."""
    text = "Para A\n\nPara B\n\nPara A\n\nPara C"
    result = remove_duplicate_paragraphs(text)
    assert result == "Para A\n\nPara B\n\nPara C"


def test_remove_duplicate_paragraphs_removes_consecutive_dupes():
    """Consecutive duplicate paragraphs must also be removed."""
    text = "Para A\n\nPara A\n\nPara B"
    result = remove_duplicate_paragraphs(text)
    assert result == "Para A\n\nPara B"


def test_remove_duplicate_paragraphs_preserves_images():
    """Image references should always be kept even if 'duplicate'."""
    text = "Some text\n\n![](/path/img.jpg)\n\nSome text\n\n![](/path/img.jpg)"
    result = remove_duplicate_paragraphs(text)
    # Image refs are always kept; the text paragraph is deduped
    assert result.count("![](/path/img.jpg)") == 2
    assert result.count("Some text") == 1


def test_remove_duplicate_paragraphs_handles_empty():
    """Empty input must return empty output."""
    assert remove_duplicate_paragraphs("") == ""
    assert remove_duplicate_paragraphs("   ") == "   "


def test_remove_duplicate_paragraphs_normalises_whitespace():
    """Paragraphs that differ only in whitespace should be treated as duplicates."""
    text = "  Hello   world  \n\nHello world\n\nThird"
    result = remove_duplicate_paragraphs(text)
    assert result == "  Hello   world  \n\nThird"


# ---------------------------------------------------------------------------
# detect_and_mark_titles
# ---------------------------------------------------------------------------


def test_detect_and_mark_titles_marks_first_paragraph():
    """A short title-case first paragraph should be marked as __HEADING__."""
    text = "The Trunchbull\n\nIn the interval, Miss Honey left the classroom."
    result = detect_and_mark_titles(text)
    assert "__HEADING__The Trunchbull__END_HEADING__" in result
    assert "In the interval" in result


def test_detect_and_mark_titles_marks_all_caps_title():
    """An ALL-CAPS short paragraph should be marked as __HEADING__."""
    text = "CHAPTER ONE\n\nThe story begins with a small girl."
    result = detect_and_mark_titles(text)
    assert "__HEADING__CHAPTER ONE__END_HEADING__" in result


def test_detect_and_mark_titles_ignores_dialogue():
    """Paragraphs starting with quotation marks must not be marked as headings."""
    text = '"Hello," she said.\n\nThe room was quiet.'
    result = detect_and_mark_titles(text)
    assert "__HEADING__" not in result
    assert "__SUBHEADING__" not in result


def test_detect_and_mark_titles_ignores_sentences():
    """Paragraphs ending with sentence punctuation must not be marked as headings."""
    text = "She walked to the door.\n\nThe room was quiet."
    result = detect_and_mark_titles(text)
    assert "__HEADING__" not in result
    assert "__SUBHEADING__" not in result


def test_detect_and_mark_titles_marks_subheadings():
    """A slightly longer title-case paragraph should be marked as __SUBHEADING__."""
    # 10 words, title case — should be subheading
    text = "A Very New Beginning For The Story That Continues Onward\n\nThe plot thickens."
    result = detect_and_mark_titles(text)
    assert "__SUBHEADING__" in result


def test_detect_and_mark_titles_ignores_image_only_paragraphs():
    """Paragraphs that are just image references must not be marked as headings."""
    text = "![](/api/images/img001.jpg)\n\nSome text follows."
    result = detect_and_mark_titles(text)
    assert "__HEADING__" not in result


def test_detect_and_mark_titles_ignores_list_items():
    """List items must not be marked as headings."""
    text = "- First item\n\n- Second item"
    result = detect_and_mark_titles(text)
    assert "__HEADING__" not in result


def test_detect_and_mark_titles_handles_empty():
    """Empty input must return empty output."""
    assert detect_and_mark_titles("") == ""


# ---------------------------------------------------------------------------
# preprocess_for_improvement
# ---------------------------------------------------------------------------


def test_preprocess_pipeline_applies_all_steps():
    """Full pipeline: dedup then mark titles."""
    text = "The Chapter\n\nSome body text.\n\nThe Chapter\n\nMore text."
    result = preprocess_for_improvement(text)
    # Duplicate removed
    assert result.count("The Chapter") == 1
    # Title marked
    assert "__HEADING__The Chapter__END_HEADING__" in result


def test_preprocess_handles_empty_input():
    """Empty input must return empty output."""
    assert preprocess_for_improvement("") == ""
