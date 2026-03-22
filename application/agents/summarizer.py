import logging
from typing import Callable

from application.agents.base import BaseAgent
from core.model.chunk import Chunk
from core.model.document import Chapter

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a precise summarizer. Summarize the following chapter text using only "
    "the information provided. Do not add external knowledge.\n\n"
    "Focus only on narrative or informational content. "
    "Ignore any study questions, comprehension exercises, before/after-reading prompts, "
    "glossary definitions, or other instructional material that may appear in the text.\n\n"
    "Structure your response in two parts:\n"
    "1. A short prose overview of 2-3 sentences.\n"
    "2. A blank line followed by a bullet-point list of 5–10 key points, "
    "each starting with '- '."
)


class SummarizerAgent(BaseAgent):
    def summarize(
        self,
        chapter: Chapter,
        chunks: list[Chunk],
        on_progress: Callable[[str], None] | None = None,
    ) -> str:
        """Summarize a chapter from its chunks.

        Args:
            chapter: Chapter metadata.
            chunks: Text chunks from the chapter.
            on_progress: Optional callback called with phase strings:
                "calling_llm" — immediately before the LLM call.
        """
        context = "\n\n".join(c.text for c in chunks)
        user = (
            f"Chapter: {chapter.title}\n\n"
            f"Text:\n{context}"
        )
        if on_progress:
            on_progress("calling_llm")
        logger.info(
            "Calling LLM to summarize chapter '%s' (%d chunks, ~%d tokens)",
            chapter.title,
            len(chunks),
            sum(len(c.text.split()) for c in chunks),
        )
        result = self._call(_SYSTEM, user)
        logger.info("Summarized chapter '%s' (%d chunks)", chapter.title, len(chunks))
        return result
