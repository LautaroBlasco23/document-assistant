import logging
from uuid import uuid4

from core.model.chunk import Chunk, ChunkMetadata
from core.model.document import Document

logger = logging.getLogger(__name__)


class ChapterAwareSplitter:
    """
    Splits a Document into Chunks using a sliding window within each chapter.
    Never crosses chapter boundaries.
    Token count = number of whitespace-separated words (fast, no tokenizer needed).
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 128):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def split(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        for chapter in document.chapters:
            chunks.extend(self._split_chapter(document, chapter))
        logger.info(
            "Split %s into %d chunks (%d chapters)",
            document.title,
            len(chunks),
            len(document.chapters),
        )
        return chunks

    def _split_chapter(self, document: Document, chapter) -> list[Chunk]:
        # Concatenate all page text, tracking character offsets per page
        parts: list[tuple[int, str]] = []  # (page_number, text)
        for page in chapter.pages:
            parts.append((page.number, page.text))

        full_text = "\n---PAGE---\n".join(text for _, text in parts)
        words = full_text.split()
        total_words = len(words)

        if total_words == 0:
            return []

        chunks: list[Chunk] = []
        start = 0
        while start < total_words:
            end = min(start + self.max_tokens, total_words)
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            # Find approximate char offsets
            start_char = len(" ".join(words[:start])) + (1 if start > 0 else 0)
            end_char = start_char + len(chunk_text)

            # Determine representative page number (from first page of chapter)
            page_number = chapter.pages[0].number if chapter.pages else 0

            metadata = ChunkMetadata(
                source_file=document.source_path,
                chapter_index=chapter.index,
                page_number=page_number,
                start_char=start_char,
                end_char=end_char,
            )
            chunks.append(
                Chunk(
                    id=str(uuid4()),
                    text=chunk_text,
                    token_count=len(chunk_words),
                    metadata=metadata,
                )
            )

            if end == total_words:
                break
            # Slide forward by (max_tokens - overlap_tokens)
            step = self.max_tokens - self.overlap_tokens
            start += max(step, 1)

        return chunks
