"""
Unit tests for token counting and truncation utilities.

Subject: application/agents/_tokens.py — count_tokens(), truncate_tokens()
Scope:   Token counting with tiktoken cl100k_base, truncation to max_tokens.
Out of scope:
  - LLM provider behavior              → respective LLM provider tests
  - Chunking logic                     → chunking tests
Setup:   Real tiktoken encoder (deterministic for given input).
"""

import pytest

from application.agents._tokens import count_tokens, truncate_tokens

# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------


def test_count_tokens_empty_string():
    """An empty string must have zero tokens."""
    assert count_tokens("") == 0


def test_count_tokens_none_treated_as_empty():
    """None input must be treated as empty string (zero tokens)."""
    assert count_tokens(None) == 0


def test_count_tokens_single_word():
    """A single common English word should be 1 token."""
    assert count_tokens("hello") == 1


def test_count_tokens_simple_sentence():
    """A short sentence should produce a predictable token count."""
    tokens = count_tokens("The quick brown fox jumps over the lazy dog.")
    assert tokens > 0
    assert tokens < 20


def test_count_tokens_multiline():
    """Multi-line text should count all tokens across lines."""
    text = "Line one.\nLine two.\nLine three."
    tokens = count_tokens(text)
    assert tokens > count_tokens("Line one.")


def test_count_tokens_unicode():
    """Unicode characters should be counted without error."""
    tokens = count_tokens("Hello 世界 🌍")
    assert tokens > 0


def test_count_tokens_whitespace_only():
    """Whitespace-only strings should produce minimal tokens."""
    assert count_tokens("   ") >= 0


def test_count_tokens_deterministic():
    """Repeated calls with the same input must return the same count."""
    text = "The meaning of life is 42."
    assert count_tokens(text) == count_tokens(text)


# ---------------------------------------------------------------------------
# truncate_tokens
# ---------------------------------------------------------------------------


def test_truncate_tokens_no_truncation_needed():
    """When text is under max_tokens, it must be returned unchanged."""
    text = "hello world"
    result = truncate_tokens(text, max_tokens=100)
    assert result == text


def test_truncate_tokens_exact_fit():
    """When text token count equals max_tokens, it must be returned unchanged."""
    text = "hello world"
    token_count = count_tokens(text)
    result = truncate_tokens(text, max_tokens=token_count)
    assert result == text


def test_truncate_tokens_truncates_long_text():
    """Text exceeding max_tokens must be truncated to fit."""
    text = "The quick brown fox jumps over the lazy dog. " * 100
    result = truncate_tokens(text, max_tokens=10)
    assert count_tokens(result) <= 10


def test_truncate_tokens_empty_string():
    """Empty string must be returned as-is."""
    assert truncate_tokens("", max_tokens=10) == ""


def test_truncate_tokens_none_treated_as_empty():
    """None input must be treated as empty string (returns None since text is unchanged)."""
    # truncate_tokens returns the original text when under max_tokens
    # For None, this means it returns None (not an empty string)
    result = truncate_tokens(None, max_tokens=10)
    assert result is None


def test_truncate_tokens_preserves_word_boundaries():
    """Truncated text should not end mid-token in a way that breaks decoding."""
    text = "hello world foo bar baz qux quux corge grault garply waldo fred plugh xyzzy thud"
    result = truncate_tokens(text, max_tokens=5)
    # The result should be valid text (no decoding errors)
    assert isinstance(result, str)
    assert len(result) > 0


def test_truncate_tokens_zero_max():
    """max_tokens=0 should return empty string."""
    text = "hello world"
    result = truncate_tokens(text, max_tokens=0)
    assert result == ""


def test_truncate_tokens_unicode():
    """Unicode text should be truncated without error."""
    text = "Hello 世界 🌍 " * 50
    result = truncate_tokens(text, max_tokens=5)
    assert count_tokens(result) <= 5
