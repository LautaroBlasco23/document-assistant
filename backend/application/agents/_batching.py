"""Shared batching utility for LLM agents."""

from core.model.chunk import Chunk


def batch_chunks_by_words(chunks: list[Chunk], max_words: int = 2500) -> list[str]:
    """Group Chunk objects into batches where each batch's total word count <= max_words.

    Chunk texts are joined with '\\n' to preserve paragraph boundaries.
    If all chunks together are <= max_words, returns a single batch.

    Returns:
        list[str]: each element is the joined text for one batch.
    """
    if not chunks:
        return []

    total_words = sum(len(c.text.split()) for c in chunks)
    if total_words <= max_words:
        return ["\n".join(c.text for c in chunks)]

    batches: list[str] = []
    current: list[str] = []
    current_words = 0

    for chunk in chunks:
        chunk_words = len(chunk.text.split())
        if current and current_words + chunk_words > max_words:
            batches.append("\n".join(current))
            current = []
            current_words = 0
        current.append(chunk.text)
        current_words += chunk_words

    if current:
        batches.append("\n".join(current))

    return batches
