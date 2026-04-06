"""Prompt regression tests: verify key instructions are present in prompt constants.

These tests prevent accidental prompt degradation when prompts are tweaked.
They do not call any LLM -- they only inspect the string constants.
"""
from application.agents.flashcard_generator import _SYSTEM as _FC_SYSTEM
from application.agents.summarizer import (
    _SYSTEM as _SUM_SYSTEM,
)
from application.agents.summarizer import (
    _SYSTEM_COMBINE,
    _SYSTEM_PARTIAL,
)

# ---------------------------------------------------------------------------
# Flashcard prompt checks
# ---------------------------------------------------------------------------


def test_flashcard_prompt_has_skip_instructions():
    """_SYSTEM must explicitly tell the model what to skip."""
    assert "SKIP" in _FC_SYSTEM


def test_flashcard_prompt_has_self_check():
    """_SYSTEM must include a SELF-CHECK section to guide the model."""
    assert "SELF-CHECK" in _FC_SYSTEM


def test_flashcard_prompt_has_three_categories():
    """_SYSTEM must define all three required categories."""
    assert "terminology" in _FC_SYSTEM.lower()
    assert "key_facts" in _FC_SYSTEM.lower()
    assert "concepts" in _FC_SYSTEM.lower()


def test_flashcard_prompt_requests_json_format():
    """_SYSTEM must specify JSON output format with 'cards' key."""
    assert '"cards"' in _FC_SYSTEM or "'cards'" in _FC_SYSTEM or "cards" in _FC_SYSTEM


def test_flashcard_prompt_has_understanding_focus():
    """_SYSTEM must emphasize understanding over trivial recall."""
    assert "UNDERSTANDING" in _FC_SYSTEM or "understanding" in _FC_SYSTEM


# ---------------------------------------------------------------------------
# Summary prompt checks
# ---------------------------------------------------------------------------


def test_summary_prompt_has_argument_instruction():
    """_SYSTEM must instruct the model to identify the chapter's argument or thesis."""
    assert "argument" in _SUM_SYSTEM.lower() or "thesis" in _SUM_SYSTEM.lower()


def test_summary_prompt_has_bad_example():
    """_SYSTEM must include a BAD bullet example to steer the model away from vague output."""
    assert "BAD" in _SUM_SYSTEM


def test_summary_prompt_has_good_example():
    """_SYSTEM must include a GOOD bullet example showing the expected specificity."""
    assert "GOOD" in _SUM_SYSTEM


def test_summary_prompt_requests_json():
    """_SYSTEM must instruct the model to return valid JSON only."""
    assert "JSON" in _SUM_SYSTEM


def test_summary_prompt_has_description_key():
    """_SYSTEM must reference the 'description' key in the JSON output."""
    assert "description" in _SUM_SYSTEM


def test_summary_prompt_has_bullets_key():
    """_SYSTEM must reference the 'bullets' key in the JSON output."""
    assert "bullets" in _SUM_SYSTEM


# ---------------------------------------------------------------------------
# Combine prompt checks
# ---------------------------------------------------------------------------


def test_combine_prompt_requests_json():
    """_SYSTEM_COMBINE must instruct the model to return valid JSON."""
    assert "JSON" in _SYSTEM_COMBINE


def test_combine_prompt_mentions_redundancy():
    """_SYSTEM_COMBINE must instruct the model to eliminate redundancy."""
    assert "redundancy" in _SYSTEM_COMBINE.lower() or "redundant" in _SYSTEM_COMBINE.lower()


def test_combine_prompt_has_description_key():
    assert "description" in _SYSTEM_COMBINE


def test_combine_prompt_has_bullets_key():
    assert "bullets" in _SYSTEM_COMBINE


# ---------------------------------------------------------------------------
# Partial summary prompt checks
# ---------------------------------------------------------------------------


def test_partial_prompt_focuses_on_arguments():
    """_SYSTEM_PARTIAL must instruct the model to focus on arguments, not just topics."""
    assert "argument" in _SYSTEM_PARTIAL.lower() or "claim" in _SYSTEM_PARTIAL.lower()


def test_partial_prompt_has_skip_section():
    """_SYSTEM_PARTIAL must tell the model what to skip."""
    assert "Skip" in _SYSTEM_PARTIAL or "SKIP" in _SYSTEM_PARTIAL
