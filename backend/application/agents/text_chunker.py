"""Paragraph-aware text chunker for LLM processing.

Splits documents at paragraph boundaries to preserve structure, with overlap
context between chunks to maintain coherence when processing large documents.
"""

import logging

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count using word count (fast, no tokenizer needed)."""
    return len(text.split())


class TextChunker:
    """Paragraph-aware text chunker with overlap for LLM processing.

    Splits text at paragraph boundaries (\n\n) to preserve structure.
    Each chunk includes overlap context from the previous chunk for continuity.
    """

    def __init__(self, max_tokens: int = 3000, overlap_tokens: int = 256):
        """
        Args:
            max_tokens: Maximum tokens per chunk (conservative to leave room for
                       system prompt + output tokens in the API call).
            overlap_tokens: Number of tokens to overlap between chunks for context.
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def should_chunk(self, text: str) -> bool:
        """Check if text exceeds max_tokens threshold and needs chunking."""
        return estimate_tokens(text) > self.max_tokens

    def chunk(self, text: str) -> list[dict]:
        """Split text into chunks with overlap context.

        Returns list of dicts:
        {
            'text': str,           # Main chunk content
            'context': str | None  # Overlap from previous chunk (for continuity)
        }
        """
        if not text.strip():
            return []

        paragraphs = text.split("\n\n")
        chunks: list[dict] = []
        current_chunk: list[str] = []
        current_tokens = 0
        previous_overlap: str | None = None

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = estimate_tokens(para)

            # Check if adding this paragraph exceeds limit
            if current_tokens + para_tokens > self.max_tokens and current_chunk:
                # Extract overlap before flushing
                overlap = self._extract_overlap_text(current_chunk)

                chunks.append({
                    "text": "\n\n".join(current_chunk),
                    "context": previous_overlap,
                })

                # Start new chunk with overlap paragraphs
                overlap_paras = self._extract_overlap_paragraphs(current_chunk)
                current_chunk = overlap_paras
                current_tokens = sum(estimate_tokens(p) for p in overlap_paras)
                previous_overlap = overlap

            current_chunk.append(para)
            current_tokens += para_tokens

        # Flush remaining
        if current_chunk:
            chunks.append({
                "text": "\n\n".join(current_chunk),
                "context": previous_overlap,
            })

        logger.info(
            "Split text into %d chunks (max_tokens=%d, overlap_tokens=%d)",
            len(chunks),
            self.max_tokens,
            self.overlap_tokens,
        )

        return chunks

    def _extract_overlap_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """Extract trailing paragraphs whose tokens <= overlap_tokens."""
        overlap_paras: list[str] = []
        tokens = 0

        for para in reversed(paragraphs):
            para_tokens = estimate_tokens(para)
            if tokens + para_tokens > self.overlap_tokens:
                break
            overlap_paras.insert(0, para)
            tokens += para_tokens

        return overlap_paras

    def _extract_overlap_text(self, paragraphs: list[str]) -> str:
        """Extract overlap text from trailing paragraphs."""
        overlap_paras = self._extract_overlap_paragraphs(paragraphs)
        return "\n\n".join(overlap_paras)
