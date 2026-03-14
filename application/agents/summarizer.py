import logging

from application.agents.base import BaseAgent
from core.model.chunk import Chunk
from core.model.document import Chapter

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a precise summarizer. Summarize the following chapter text using only "
    "the information provided. Output a concise bullet-point list (5–10 points). "
    "Do not add external knowledge."
)


class SummarizerAgent(BaseAgent):
    def summarize(self, chapter: Chapter, chunks: list[Chunk]) -> str:
        context = "\n\n".join(c.text for c in chunks)
        user = (
            f"Chapter: {chapter.title}\n\n"
            f"Text:\n{context}"
        )
        result = self._call(_SYSTEM, user)
        logger.info("Summarized chapter '%s' (%d chunks)", chapter.title, len(chunks))
        return result
