import logging
import re
from uuid import uuid4

from core.model.chunk import Chunk, ChunkMetadata
from core.model.document import Document

logger = logging.getLogger(__name__)

_PAGE_MARKER = "---PAGE---"


class ChapterAwareSplitter:
    """
    Splits a Document into Chunks using paragraph-aware grouping within each chapter.
    Never crosses chapter boundaries.
    Token count = number of whitespace-separated words (fast, no tokenizer needed).
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 128):
        self.max_tokens = max_tokens
        # Guard: overlap must be strictly less than max_tokens to prevent infinite loops.
        self.overlap_tokens = min(overlap_tokens, max_tokens - 1)

    def split(self, document: Document, chapter_indices: set[int] | None = None) -> list[Chunk]:
        chapters = document.chapters
        if chapter_indices is not None:
            chapters = [c for c in chapters if c.index in chapter_indices]
        chunks: list[Chunk] = []
        for chapter in chapters:
            chunks.extend(self._split_chapter(document, chapter))
        logger.info(
            "Split %s into %d chunks (%d chapters%s)",
            document.title,
            len(chunks),
            len(chapters),
            f" filtered from {len(document.chapters)}" if chapter_indices else "",
        )
        return chunks

    def _split_chapter(self, document: Document, chapter) -> list[Chunk]:
        # Build (page_number, page_text) pairs
        parts: list[tuple[int, str]] = [
            (page.number, page.text) for page in chapter.pages
        ]

        if not parts:
            return []

        # Build a flat list of (page_number, paragraph_text, word_count)
        paragraphs: list[tuple[int, str, int]] = []
        for pg_num, pg_text in parts:
            # Strip any residual PAGE markers from page text before splitting
            clean_pg = pg_text.replace(_PAGE_MARKER, "").strip()
            for para in re.split(r"\n\s*\n+", clean_pg):
                para = para.strip()
                if para:
                    w = len(para.split())
                    paragraphs.append((pg_num, para, w))

        if not paragraphs:
            return []

        chunks: list[Chunk] = []
        # Approximate char cursor for start_char / end_char metadata
        char_cursor = 0

        buf: list[tuple[int, str, int]] = []
        buf_words = 0

        def _flush(buf: list[tuple[int, str, int]]) -> Chunk:
            nonlocal char_cursor
            chunk_text = "\n\n".join(t for _, t, _ in buf)
            # Scrub any residual PAGE markers; preserve paragraph breaks.
            chunk_text = chunk_text.replace(_PAGE_MARKER, "")
            chunk_text = re.sub(r"[ \t]+", " ", chunk_text).strip()
            token_count = len(chunk_text.split())
            pg = buf[0][0]
            start_char = char_cursor
            end_char = start_char + len(chunk_text)
            char_cursor = end_char + 2  # account for the "\n\n" separator between chunks
            metadata = ChunkMetadata(
                source_file=document.file_hash,
                chapter_index=chapter.index,
                page_number=pg,
                start_char=start_char,
                end_char=end_char,
            )
            return Chunk(
                id=str(uuid4()),
                text=chunk_text,
                token_count=token_count,
                metadata=metadata,
            )

        def _seed_overlap(
            buf: list[tuple[int, str, int]],
        ) -> tuple[list[tuple[int, str, int]], int]:
            """Return trailing paragraphs whose cumulative words <= overlap_tokens."""
            seed: list[tuple[int, str, int]] = []
            seed_words = 0
            for item in reversed(buf):
                if seed_words + item[2] <= self.overlap_tokens:
                    seed.insert(0, item)
                    seed_words += item[2]
                else:
                    break
            return seed, seed_words

        def _word_window_fallback(pg_num: int, para_text: str) -> list[Chunk]:
            """Fall back to sliding-window chunking for a single oversized paragraph."""
            nonlocal char_cursor
            words = para_text.split()
            total = len(words)
            result: list[Chunk] = []
            start = 0
            while start < total:
                end = min(start + self.max_tokens, total)
                chunk_text = " ".join(words[start:end])
                token_count = len(chunk_text.split())
                s_char = char_cursor
                e_char = s_char + len(chunk_text)
                char_cursor = e_char + 2
                metadata = ChunkMetadata(
                    source_file=document.file_hash,
                    chapter_index=chapter.index,
                    page_number=pg_num,
                    start_char=s_char,
                    end_char=e_char,
                )
                result.append(
                    Chunk(
                        id=str(uuid4()),
                        text=chunk_text,
                        token_count=token_count,
                        metadata=metadata,
                    )
                )
                if end == total:
                    break
                step = self.max_tokens - self.overlap_tokens
                start += max(step, 1)
            return result

        for pg_num, para_text, w in paragraphs:
            if buf_words + w > self.max_tokens and buf:
                # Flush the current buffer
                chunks.append(_flush(buf))
                # Rewind for overlap
                buf, buf_words = _seed_overlap(buf)

            if w > self.max_tokens:
                # Single paragraph exceeds max_tokens — flush buf first (already done
                # above if buf was non-empty), then fall back to word-window.
                if buf:
                    chunks.append(_flush(buf))
                    buf, buf_words = [], 0
                chunks.extend(_word_window_fallback(pg_num, para_text))
            else:
                buf.append((pg_num, para_text, w))
                buf_words += w

        # Flush remaining buffer
        if buf:
            chunks.append(_flush(buf))

        return chunks
