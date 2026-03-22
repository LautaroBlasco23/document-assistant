import logging

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a knowledgeable reading assistant helping a user understand a book they "
    "are studying. Answer the user's question using ONLY the provided context from "
    "the book.\n\n"
    "Rules:\n"
    "- Base your answer strictly on the provided text. Do not add external knowledge.\n"
    "- If the context does not contain enough information, say so clearly and suggest "
    "what the user could look for.\n"
    "- Reference specific details, examples, or page numbers from the text to support "
    "your answer.\n"
    "- When explaining concepts, connect them to other ideas mentioned in the context "
    "to help the reader build a mental model.\n"
    "- Be concise but thorough — prioritize clarity over brevity."
)


class QAAgent(BaseAgent):
    def answer(
        self,
        query: str,
        chunks: list[Chunk],
        chapter_title: str = "",
        document_title: str = "",
    ) -> str:
        context_parts = []
        if document_title:
            context_parts.append(f"Document: {document_title}")
        if chapter_title:
            context_parts.append(f"Chapter: {chapter_title}")

        context_parts.append("\nRelevant passages:")
        for c in chunks:
            page = c.metadata.page_number if c.metadata else "?"
            context_parts.append(f"\n[p.{page}] {c.text}")

        context = "\n".join(context_parts)
        user = f"{context}\n\nQuestion: {query}"
        result = self._call(_SYSTEM, user)
        logger.info("Answered query: %s...", query[:60])
        return result
