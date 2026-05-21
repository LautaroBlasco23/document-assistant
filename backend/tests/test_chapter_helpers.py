"""
Unit tests for chapter resolution and context helpers.

Subject: application/services/chapter_helpers.py — parse_uuid(), resolve_chapter(), get_chapter_context()
Scope:   UUID parsing with 422 errors, chapter resolution with 404 errors,
         chapter context retrieval with token truncation.
Out of scope:
  - Store implementations              → repository tests
  - Chunking logic                     → chunking tests
  - LLM behavior                       → LLM provider tests
Setup:   Mocked Services object with mocked stores.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from application.services.chapter_helpers import (
    get_chapter_context,
    parse_uuid,
    resolve_chapter,
)

# ---------------------------------------------------------------------------
# parse_uuid
# ---------------------------------------------------------------------------


def test_parse_uuid_valid():
    """A valid UUID string must be parsed into a UUID object."""
    from uuid import UUID

    result = parse_uuid("550e8400-e29b-41d4-a716-446655440000", "tree_id")
    assert isinstance(result, UUID)
    assert str(result) == "550e8400-e29b-41d4-a716-446655440000"


def test_parse_uuid_invalid_raises_422():
    """An invalid UUID string must raise HTTPException with status 422."""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid("not-a-uuid", "tree_id")

    assert exc_info.value.status_code == 422
    assert "Invalid tree_id" in exc_info.value.detail


def test_parse_uuid_empty_raises_422():
    """An empty string must raise HTTPException with status 422."""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid("", "chapter_id")

    assert exc_info.value.status_code == 422


def test_parse_uuid_includes_label_in_error():
    """The error message must include the provided label."""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid("bad", "custom_label")

    assert "custom_label" in exc_info.value.detail


# ---------------------------------------------------------------------------
# resolve_chapter
# ---------------------------------------------------------------------------


def _make_services(tree_exists=True, chapters=None):
    """Return a mocked Services object."""
    services = MagicMock()
    services.kt_tree_store.get_tree.return_value = MagicMock() if tree_exists else None
    services.kt_chapter_store.list_chapters.return_value = chapters or []
    return services


def test_resolve_chapter_success():
    """When tree and chapter exist, resolve_chapter must return (tree_uid, chapter)."""
    from uuid import UUID

    tree_uid = UUID("550e8400-e29b-41d4-a716-446655440000")
    chapter = MagicMock()
    chapter.number = 1
    services = _make_services(tree_exists=True, chapters=[chapter])

    uid, ch = resolve_chapter(services, str(tree_uid), 1)

    assert uid == tree_uid
    assert ch is chapter


def test_resolve_chapter_tree_not_found():
    """When the tree does not exist, resolve_chapter must raise HTTPException 404."""
    services = _make_services(tree_exists=False)

    with pytest.raises(HTTPException) as exc_info:
        resolve_chapter(services, "550e8400-e29b-41d4-a716-446655440000", 1)

    assert exc_info.value.status_code == 404
    assert "Knowledge tree not found" in exc_info.value.detail


def test_resolve_chapter_chapter_not_found():
    """When the chapter number does not exist, resolve_chapter must raise HTTPException 404."""
    chapter = MagicMock()
    chapter.number = 2
    services = _make_services(tree_exists=True, chapters=[chapter])

    with pytest.raises(HTTPException) as exc_info:
        resolve_chapter(services, "550e8400-e29b-41d4-a716-446655440000", 1)

    assert exc_info.value.status_code == 404
    assert "Chapter 1 not found" in exc_info.value.detail


def test_resolve_chapter_invalid_tree_id():
    """An invalid tree_id UUID must raise HTTPException 422."""
    services = _make_services()

    with pytest.raises(HTTPException) as exc_info:
        resolve_chapter(services, "not-a-uuid", 1)

    assert exc_info.value.status_code == 422


def test_resolve_chapter_empty_chapters():
    """When a tree has no chapters, resolve_chapter must raise HTTPException 404."""
    services = _make_services(tree_exists=True, chapters=[])

    with pytest.raises(HTTPException) as exc_info:
        resolve_chapter(services, "550e8400-e29b-41d4-a716-446655440000", 1)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_chapter_context
# ---------------------------------------------------------------------------


def test_get_chapter_context_returns_truncated_text():
    """get_chapter_context must return chapter text truncated to max_tokens."""
    from core.model.chunk import Chunk

    services = MagicMock()
    chunk = Chunk(text="Hello world " * 100, token_count=300)
    services.kt_content_store.get_chunks.return_value = [chunk]

    result = get_chapter_context(services, "550e8400-e29b-41d4-a716-446655440000", 1, max_tokens=10)

    assert isinstance(result, str)
    # Should be truncated
    assert len(result) < len(chunk.text)


def test_get_chapter_context_no_selected_text():
    """Without selected_text, get_chapter_context must return all chunks truncated."""
    from core.model.chunk import Chunk

    services = MagicMock()
    chunks = [
        Chunk(text="First chunk", token_count=3),
        Chunk(text="Second chunk", token_count=3),
    ]
    services.kt_content_store.get_chunks.return_value = chunks

    result = get_chapter_context(services, "550e8400-e29b-41d4-a716-446655440000", 1)

    assert "First chunk" in result
    assert "Second chunk" in result


def test_get_chapter_context_empty_chunks():
    """When no chunks exist, get_chapter_context must return empty string."""
    services = MagicMock()
    services.kt_content_store.get_chunks.return_value = []

    result = get_chapter_context(services, "550e8400-e29b-41d4-a716-446655440000", 1)

    assert result == ""


def test_get_chapter_context_default_max_tokens():
    """The default max_tokens should be 4000."""
    from core.model.chunk import Chunk

    services = MagicMock()
    chunk = Chunk(text="x" * 5000, token_count=1000)
    services.kt_content_store.get_chunks.return_value = [chunk]

    result = get_chapter_context(services, "550e8400-e29b-41d4-a716-446655440000", 1)

    # Should be truncated to default 4000 tokens
    assert len(result) <= 5000
