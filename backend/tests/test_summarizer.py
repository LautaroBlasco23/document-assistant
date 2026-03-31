"""Unit tests for SummarizerAgent: parsing, batching, prompt construction."""
import json
from unittest.mock import MagicMock

import pytest

from application.agents.summarizer import SummarizerAgent, _batch_chunks, _MAX_WORDS_PER_CALL
from core.model.chunk import Chunk, ChunkMetadata
from core.model.document import Chapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(text: str, page_number: int = 1) -> Chunk:
    return Chunk(
        text=text,
        token_count=len(text.split()),
        metadata=ChunkMetadata(
            source_file="test-hash",
            chapter_index=0,
            page_number=page_number,
            start_char=0,
            end_char=len(text),
        ),
    )


def _make_chapter(title: str = "Chapter 1") -> Chapter:
    return Chapter(index=0, title=title, pages=[])


def _make_agent(return_value: str) -> SummarizerAgent:
    """Create a SummarizerAgent whose LLM always returns return_value."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = return_value
    return SummarizerAgent(mock_llm)


# ---------------------------------------------------------------------------
# Test parsing: valid JSON
# ---------------------------------------------------------------------------


def test_parse_valid_json_summary():
    response = json.dumps({
        "description": "This chapter examines how working memory constrains problem solving.",
        "bullets": [
            "Working memory can hold roughly 4 chunks of information at once.",
            "Chunking reduces cognitive load by grouping related items.",
        ],
    })
    agent = _make_agent(response)
    result = agent.summarize(_make_chapter(), [_make_chunk("some text " * 100)])
    assert "working memory" in result["description"].lower()
    assert len(result["bullets"]) == 2
    assert "## Overview" in result["content"]
    assert "## Key Takeaways" in result["content"]


def test_parse_double_encoded_json():
    """Summarizer should handle double-stringified JSON responses."""
    inner = {"description": "The chapter covers neural plasticity.", "bullets": ["Plasticity allows rewiring."]}
    response = json.dumps(json.dumps(inner))  # double-encoded
    agent = _make_agent(response)
    result = agent.summarize(_make_chapter(), [_make_chunk("some text " * 100)])
    assert result["description"] == "The chapter covers neural plasticity."


def test_parse_fallback_on_invalid_json():
    """Returns raw text as content when JSON cannot be parsed."""
    agent = _make_agent("not valid json at all")
    result = agent.summarize(_make_chapter(), [_make_chunk("some text " * 100)])
    assert result["description"] == ""
    assert result["bullets"] == []
    assert result["content"] == "not valid json at all"


# ---------------------------------------------------------------------------
# Test _batch_chunks
# ---------------------------------------------------------------------------


def test_batch_chunks_respects_word_limit():
    chunks = [_make_chunk("word " * 1000) for _ in range(5)]
    batches = _batch_chunks(chunks, max_words=3500)
    # 5 chunks x 1000 words = 5000 words; should split into batches of ~3500 each
    assert len(batches) == 2
    # Each batch should not exceed max_words (except for single oversized chunks)
    for batch in batches:
        total = sum(len(c.text.split()) for c in batch)
        assert total <= 3500 or len(batch) == 1


def test_batch_chunks_empty():
    assert _batch_chunks([], max_words=3500) == []


def test_batch_chunks_all_fit_in_one():
    chunks = [_make_chunk("short text") for _ in range(5)]
    batches = _batch_chunks(chunks, max_words=3500)
    assert len(batches) == 1


# ---------------------------------------------------------------------------
# Test prompt construction
# ---------------------------------------------------------------------------


def test_single_batch_prompt_includes_document_title():
    """The user prompt should include document title and chapter title."""
    response = json.dumps({"description": "A summary.", "bullets": ["Point one."]})
    mock_llm = MagicMock()
    mock_llm.chat.return_value = response
    agent = SummarizerAgent(mock_llm)

    agent.summarize(
        _make_chapter("Introduction"),
        [_make_chunk("some text " * 50)],
        document_title="Learning Science",
        document_type="textbook",
    )

    call_args = mock_llm.chat.call_args
    user_prompt = call_args[0][1]  # second positional arg
    assert "Learning Science" in user_prompt
    assert "Introduction" in user_prompt
    assert "textbook" in user_prompt
