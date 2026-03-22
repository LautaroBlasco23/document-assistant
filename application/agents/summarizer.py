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
    "You are an expert reading assistant that creates learning-oriented summaries. "
    "Your goal is to help the reader deeply understand and retain the material.\n\n"
    "Rules:\n"
    "- Use ONLY information from the provided text. Do not add external knowledge.\n"
    "- Ignore study questions, comprehension exercises, before/after-reading prompts, "
    "glossary definitions, or other instructional material embedded in the text.\n"
    "- Write in clear, accessible language.\n\n"
    "Structure your response EXACTLY as follows:\n\n"
    "## Overview\n"
    "A 3-4 sentence paragraph explaining what this chapter covers, why it matters, "
    "and how it connects to the broader subject.\n\n"
    "## Key Concepts\n"
    "A bullet list of 5-8 central ideas or concepts introduced in this chapter. "
    "For each concept, write the concept name in bold followed by a 1-2 sentence "
    "explanation. Example:\n"
    "- **Concept Name**: What it is and why it matters in context.\n\n"
    "## Important Details\n"
    "A bullet list of 3-5 specific facts, examples, dates, names, or evidence "
    "presented in the chapter that support the key concepts.\n\n"
    "## Connections & Implications\n"
    "2-3 sentences describing how the ideas in this chapter relate to each other "
    "and what implications or conclusions the author draws."
)

_SYSTEM_COMBINE = (
    "You are an expert reading assistant. You are given several partial summaries "
    "of sections from the same chapter. Merge them into a single coherent summary "
    "using only the information provided.\n\n"
    "Structure your response EXACTLY as follows:\n\n"
    "## Overview\n"
    "A 3-4 sentence paragraph explaining what this chapter covers, why it matters, "
    "and how it connects to the broader subject.\n\n"
    "## Key Concepts\n"
    "A bullet list of 5-8 central ideas. For each, write the concept name in bold "
    "followed by a 1-2 sentence explanation.\n\n"
    "## Important Details\n"
    "A bullet list of 3-5 specific facts, examples, or evidence from the chapter.\n\n"
    "## Connections & Implications\n"
    "2-3 sentences on how the ideas relate to each other and what conclusions "
    "the author draws."
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
    ) -> str:
        """Summarize a chapter from its chunks using map-reduce if needed.

        Args:
            chapter: Chapter metadata.
            chunks: Text chunks from the chapter.
            on_progress: Optional callback called with phase strings.
            document_title: Title of the document for context.
        """
        total_words = sum(len(c.text.split()) for c in chunks)
        batches = _batch_chunks(chunks, _MAX_WORDS_PER_CALL)

        if on_progress:
            on_progress("calling_llm")

        # Build context header
        header = f"Chapter: {chapter.title}"
        if document_title:
            header = f"Document: {document_title}\n{header}"

        if len(batches) == 1:
            context = "\n\n".join(c.text for c in chunks)
            user = f"{header}\n\nText:\n{context}"
            logger.info(
                "Calling LLM to summarize chapter '%s' (%d chunks, ~%d tokens)",
                chapter.title,
                len(chunks),
                total_words,
            )
            result = self._call(_SYSTEM, user)
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
            result = self._call(_SYSTEM_COMBINE, user)

        logger.info("Summarized chapter '%s' (%d chunks)", chapter.title, len(chunks))
        return result
