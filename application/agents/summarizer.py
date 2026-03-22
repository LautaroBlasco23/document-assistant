import json
import logging
from typing import Callable

from application.agents.base import BaseAgent
from core.model.chunk import Chunk
from core.model.document import Chapter

logger = logging.getLogger(__name__)

# Conservative token budget per LLM call (words ≈ tokens for English).
# Leaves room for system prompt (~300 tokens) and response (~600 tokens)
# within an 8192-token context window.
_MAX_WORDS_PER_CALL = 3500

_SYSTEM = (
    "You are an expert reading assistant that creates learning-oriented summaries.\n\n"
    "Analyze the provided chapter text and return a JSON object with exactly two keys:\n\n"
    '1. "description": A 3-4 sentence paragraph explaining what this chapter covers, '
    "why it matters, and how it connects to the broader subject. "
    "Write in clear, accessible language.\n\n"
    '2. "bullets": An array of 6-10 strings, each being a key takeaway, important concept, '
    "or notable detail from the chapter. "
    "Each bullet should be a complete, self-contained sentence.\n\n"
    "Rules:\n"
    "- Use ONLY information from the provided text. Do not add external knowledge.\n"
    "- Ignore study questions, exercises, glossary definitions, or instructional material.\n"
    "- Return valid JSON only. No markdown, no code fences."
)

_SYSTEM_COMBINE = (
    "You are an expert reading assistant. You are given several partial summaries "
    "of sections from the same chapter. Merge them into a single coherent summary "
    "using only the information provided.\n\n"
    "Return a JSON object with exactly two keys:\n\n"
    '1. "description": A 3-4 sentence paragraph explaining what this chapter covers, '
    "why it matters, and how it connects to the broader subject.\n\n"
    '2. "bullets": An array of 6-10 strings, each being a key takeaway, important concept, '
    "or notable detail from the chapter. "
    "Each bullet should be a complete, self-contained sentence.\n\n"
    "Rules:\n"
    "- Use only the information from the provided partial summaries.\n"
    "- Return valid JSON only. No markdown, no code fences."
)

_SYSTEM_PARTIAL = (
    "You are an expert reading assistant. Summarize the following excerpt from a "
    "chapter to help a reader understand and retain the material.\n\n"
    "Rules:\n"
    "- Use ONLY information from the provided text.\n"
    "- Ignore study questions, exercises, glossary definitions, or instructional material.\n\n"
    "Write:\n"
    "1. A 2-3 sentence overview of what this section covers.\n"
    "2. A bullet list of 3-5 key concepts or ideas, each with the concept name "
    "in bold and a brief explanation.\n"
    "3. A bullet list of 2-3 important specific details (facts, examples, evidence)."
)


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
            raw = self._call_json(_SYSTEM, user)
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
                partial_summaries.append(self._call(_SYSTEM_PARTIAL, user))

            combined = "\n\n---\n\n".join(
                f"Part {i}:\n{s}" for i, s in enumerate(partial_summaries, 1)
            )
            user = f"{header}\n\nPartial summaries:\n{combined}"
            logger.info(
                "Combining %d partial summaries for chapter '%s'",
                len(partial_summaries),
                chapter.title,
            )
            raw = self._call_json(_SYSTEM_COMBINE, user)

        try:
            parsed = json.loads(raw)
            description = parsed.get("description", "")
            bullets = parsed.get("bullets", [])
            if not isinstance(bullets, list):
                bullets = []
        except (json.JSONDecodeError, AttributeError):
            logger.warning("LLM returned non-JSON summary; falling back to raw text")
            description = ""
            bullets = []
            content = raw
            return {"description": description, "bullets": bullets, "content": content}

        content = f"## Overview\n\n{description}\n\n## Key Takeaways\n\n"
        content += "\n".join(f"- {b}" for b in bullets)

        logger.info("Summarized chapter '%s' (%d chunks)", chapter.title, len(chunks))
        return {"description": description, "bullets": bullets, "content": content}
