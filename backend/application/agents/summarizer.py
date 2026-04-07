import json
import logging
from typing import Callable

from application.agents.base import BaseAgent
from application.prompts import SUMMARY_SYSTEM, SUMMARY_SYSTEM_COMBINE, SUMMARY_SYSTEM_PARTIAL
from core.model.chunk import Chunk
from core.model.document import Chapter

logger = logging.getLogger(__name__)

# Conservative token budget per LLM call (words ≈ tokens for English).
# Leaves room for system prompt (~300 tokens) and response (~600 tokens)
# within an 8192-token context window.
_MAX_WORDS_PER_CALL = 3500


def _batch_chunks(chunks: list[Chunk], max_words: int) -> list[list[Chunk]]:
    """Group chunks into batches that stay within max_words."""
    batches: list[list[Chunk]] = []
    current: list[Chunk] = []
    current_words = 0
    for chunk in chunks:
        chunk_words = len(chunk.text.split())
        if current and current_words + chunk_words > max_words:
            batches.append(current)
            current = []
            current_words = 0
        current.append(chunk)
        current_words += chunk_words
    if current:
        batches.append(current)
    return batches


class SummarizerAgent(BaseAgent):
    def summarize(
        self,
        chapter: Chapter,
        chunks: list[Chunk],
        on_progress: Callable[[str], None] | None = None,
        document_title: str = "",
        document_description: str = "",
        document_type: str = "",
    ) -> dict:
        """Summarize a chapter from its chunks using map-reduce if needed.

        Returns a dict with keys: description (str), bullets (list[str]), content (str).
        content is a backward-compatible markdown string built from description and bullets.

        Args:
            chapter: Chapter metadata.
            chunks: Text chunks from the chapter.
            on_progress: Optional callback called with phase strings.
            document_title: Title of the document for context.
            document_description: User-provided description of the document for context.
            document_type: Type of document (book, paper, documentation, etc.) for context.
        """
        total_words = sum(len(c.text.split()) for c in chunks)
        batches = _batch_chunks(chunks, _MAX_WORDS_PER_CALL)

        if on_progress:
            on_progress("calling_llm")

        # Build context header
        header = f"Chapter: {chapter.title}"
        if document_title:
            header = f"Document: {document_title}\n{header}"
        if document_type:
            header += f"\nDocument type: {document_type}"
        if document_description:
            header += f"\nDocument context: {document_description}"

        if len(batches) == 1:
            context = "\n\n".join(c.text for c in chunks)
            user = f"{header}\n\nText:\n{context}"
            logger.info(
                "Calling LLM to summarize chapter '%s' (%d chunks, ~%d tokens)",
                chapter.title,
                len(chunks),
                total_words,
            )
            raw = self._call_json_with_retry(SUMMARY_SYSTEM, user)
        else:
            logger.info(
                "Chapter '%s' too large (%d words); splitting into %d batches",
                chapter.title,
                total_words,
                len(batches),
            )
            partial_summaries: list[str] = []
            for i, batch in enumerate(batches, 1):
                context = "\n\n".join(c.text for c in batch)
                user = f"{header} (part {i}/{len(batches)})\n\nText:\n{context}"
                logger.info(
                    "Summarizing batch %d/%d for chapter '%s' (~%d words)",
                    i,
                    len(batches),
                    chapter.title,
                    sum(len(c.text.split()) for c in batch),
                )
                partial_summaries.append(self._call(SUMMARY_SYSTEM_PARTIAL, user))

            combined = "\n\n---\n\n".join(
                f"Part {i}:\n{s}" for i, s in enumerate(partial_summaries, 1)
            )
            user = f"{header}\n\nPartial summaries:\n{combined}"
            logger.info(
                "Combining %d partial summaries for chapter '%s'",
                len(partial_summaries),
                chapter.title,
            )
            raw = self._call_json_with_retry(SUMMARY_SYSTEM_COMBINE, user)

        try:
            parsed = json.loads(raw)
            # Handle double-stringified response (entire JSON wrapped in quotes)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)

            description = parsed.get("description", "")
            bullets = parsed.get("bullets", [])

            # Handle bullets stored as JSON string instead of list
            if isinstance(bullets, str):
                try:
                    bullets = json.loads(bullets)
                except (json.JSONDecodeError, TypeError):
                    bullets = []
            if not isinstance(bullets, list):
                bullets = []

            # Handle double-encoded JSON (LLM sometimes returns JSON as a string)
            if isinstance(description, str) and description.startswith('{"'):
                try:
                    inner = json.loads(description)
                    description = inner.get("description", description)
                    if isinstance(inner.get("bullets"), list):
                        bullets = inner["bullets"]
                except json.JSONDecodeError:
                    pass  # Keep original description if parsing fails
        except (json.JSONDecodeError, AttributeError, TypeError):
            logger.warning("LLM returned non-JSON summary; falling back to raw text")
            description = ""
            bullets = []
            content = raw
            return {"description": description, "bullets": bullets, "content": content}

        content = f"## Overview\n\n{description}\n\n## Key Takeaways\n\n"
        content += "\n".join(f"- {b}" for b in bullets)

        logger.info("Summarized chapter '%s' (%d chunks)", chapter.title, len(chunks))
        return {"description": description, "bullets": bullets, "content": content}
