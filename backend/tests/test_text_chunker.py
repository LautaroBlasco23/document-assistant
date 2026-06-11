"""Unit tests for TextChunker.

Subject: application/agents/text_chunker.py
Scope:   chunking logic, overlap handling, token estimation.
"""

from application.agents.text_chunker import TextChunker, estimate_tokens


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_single_word(self):
        assert estimate_tokens("hello") == 1

    def test_multiple_words(self):
        assert estimate_tokens("hello world foo bar") == 4

    def test_whitespace_handling(self):
        assert estimate_tokens("  hello   world  ") == 2


class TestTextChunker:
    def test_should_chunk_false_for_short_text(self):
        chunker = TextChunker(max_tokens=100)
        assert chunker.should_chunk("Short text.") is False

    def test_should_chunk_true_for_long_text(self):
        chunker = TextChunker(max_tokens=5)
        text = "word " * 10  # 10 words
        assert chunker.should_chunk(text) is True

    def test_chunk_empty_text(self):
        chunker = TextChunker(max_tokens=100)
        assert chunker.chunk("") == []

    def test_chunk_single_paragraph(self):
        chunker = TextChunker(max_tokens=100)
        text = "This is a paragraph."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "This is a paragraph."
        assert chunks[0]["context"] is None

    def test_chunk_respects_paragraph_boundaries(self):
        chunker = TextChunker(max_tokens=4)  # ~4 words per chunk
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        # Each chunk should be complete paragraphs
        for chunk in chunks:
            assert "\n" not in chunk["text"].replace("\n\n", "")

    def test_chunk_includes_overlap_context(self):
        chunker = TextChunker(max_tokens=6, overlap_tokens=4)
        text = "First sentence here.\n\nSecond sentence there.\n\nThird sentence elsewhere."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        # Second chunk should have context from first
        assert chunks[1]["context"] is not None
        assert len(chunks[1]["context"]) > 0

    def test_chunk_first_chunk_has_no_context(self):
        chunker = TextChunker(max_tokens=6, overlap_tokens=4)
        text = "First sentence.\n\nSecond sentence.\n\nThird sentence."
        chunks = chunker.chunk(text)
        assert chunks[0]["context"] is None

    def test_chunk_preserves_paragraph_structure(self):
        chunker = TextChunker(max_tokens=8, overlap_tokens=3)
        text = "Para one.\n\nPara two.\n\nPara three.\n\nPara four."
        chunks = chunker.chunk(text)
        # All original content should appear across chunks
        combined = "\n\n".join(c["text"] for c in chunks)
        assert "Para one." in combined
        assert "Para two." in combined
        assert "Para three." in combined
        assert "Para four." in combined

    def test_chunk_handles_single_huge_paragraph(self):
        chunker = TextChunker(max_tokens=5, overlap_tokens=2)
        # Single paragraph that exceeds max_tokens
        text = "word " * 20
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1
        # Content should be preserved
        combined = " ".join(c["text"] for c in chunks)
        assert "word" in combined
