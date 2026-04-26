"""
Subject: application/agents/_batching.py — batch_chunks_by_words
Scope:   Grouping chunks into word-count-limited batches
Out of scope:
  - LLM prompt dispatch or JSON parsing   → test_base_agent.py
  - question generation orchestration     → test_question_generator_agent.py
Setup:   Pure function; no external dependencies.
"""


from application.agents._batching import batch_chunks_by_words
from core.model.chunk import Chunk, ChunkMetadata


def _chunk(text: str) -> Chunk:
    """Build a Chunk with the given text."""
    return Chunk(text=text, metadata=ChunkMetadata(
        source_file="test", chapter_index=0, page_number=1, start_char=0, end_char=len(text)
    ))


# Returns a single batch when the total word count is under the limit.
def test_single_batch_under_limit():
    chunks = [_chunk("one two three"), _chunk("four five six")]
    batches = batch_chunks_by_words(chunks, max_words=100)
    assert len(batches) == 1
    assert "one two three" in batches[0]
    assert "four five six" in batches[0]


# Splits into multiple batches when the total word count exceeds the limit.
def test_multi_batch_over_limit():
    chunks = [
        _chunk("a b c d e"),   # 5 words
        _chunk("f g h i j"),   # 5 words
        _chunk("k l m n o"),   # 5 words
    ]
    batches = batch_chunks_by_words(chunks, max_words=10)
    assert len(batches) == 2
    assert "a b c d e" in batches[0]
    assert "f g h i j" in batches[0]
    assert "k l m n o" in batches[1]


# Splits exactly at the boundary when adding the next chunk would exceed max_words.
def test_exact_boundary():
    chunks = [
        _chunk("one two"),      # 2 words
        _chunk("three four"),   # 2 words
        _chunk("five six"),     # 2 words
    ]
    batches = batch_chunks_by_words(chunks, max_words=4)
    assert len(batches) == 2
    assert "one two" in batches[0]
    assert "three four" in batches[0]
    assert "five six" in batches[1]


# Returns an empty list when the input chunks list is empty.
def test_empty_input():
    batches = batch_chunks_by_words([], max_words=10)
    assert batches == []


# Handles a single chunk that alone exceeds the limit by placing it in its own batch.
def test_single_chunk_over_limit():
    text = " ".join(["word"] * 20)
    chunks = [_chunk(text)]
    batches = batch_chunks_by_words(chunks, max_words=10)
    assert len(batches) == 1
    assert batches[0] == text
