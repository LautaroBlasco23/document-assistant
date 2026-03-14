import logging

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a helpful assistant. Answer the user's question using ONLY the provided context. "
    "If the context does not contain enough information to answer, say so clearly. "
    "Be concise and accurate."
)


class QAAgent(BaseAgent):
    def answer(self, query: str, chunks: list[Chunk]) -> str:
        context = "\n\n".join(
            f"[p.{c.metadata.page_number if c.metadata else '?'}] {c.text}"
            for c in chunks
        )
        user = f"Context:\n{context}\n\nQuestion: {query}"
        result = self._call(_SYSTEM, user)
        logger.info("Answered query: %s...", query[:60])
        return result
