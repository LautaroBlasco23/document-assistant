import logging

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a knowledgeable assistant helping the user understand a document. "
    "Answer the user's question based ONLY on the provided context from the document.\n\n"
    "Rules:\n"
    "- Cite page numbers using [p.N] when referencing information from a specific page.\n"
    "- If the context does not contain enough information to answer the question, "
    "say exactly: \"I don't have enough information to answer this.\"\n"
    "- Keep your answer concise but thorough.\n"
    "- Do NOT make up information that is not present in the provided context.\n"
    "- Respond in plain text (no markdown unless it genuinely helps readability)."
)


class ChatAgent(BaseAgent):
    def answer(
        self,
        query: str,
        chunks: list[Chunk],
        history: list[dict] | None = None,
        document_title: str = "",
        chapter_title: str = "",
    ) -> str:
        """Answer a user query based on retrieved document chunks.

        Args:
            query: The user's question.
            chunks: Retrieved chunks providing context for the answer.
            history: Optional list of prior messages as dicts with 'role' and 'content'.
                     Only the last 6 messages are included to keep the prompt manageable.
            document_title: Title of the document for context.
            chapter_title: Title of the chapter (if scoped to one) for context.

        Returns:
            The LLM-generated answer as a plain text string.
        """
        # Build context header
        header_parts = []
        if document_title:
            header_parts.append(f"Document: {document_title}")
        if chapter_title:
            header_parts.append(f"Chapter: {chapter_title}")
        header = "\n".join(header_parts)

        # Format chunks as numbered context blocks with page references
        context_blocks = []
        for i, chunk in enumerate(chunks, start=1):
            page_ref = chunk.metadata.page_number if chunk.metadata else "?"
            context_blocks.append(f"[{i}] [p.{page_ref}] {chunk.text}")
        context = "\n\n".join(context_blocks)

        # Build history section (last 6 messages)
        history_section = ""
        if history:
            recent = history[-6:]
            history_lines = []
            for msg in recent:
                role = msg.get("role", "user").capitalize()
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            history_section = "Prior conversation:\n" + "\n".join(history_lines) + "\n\n"

        # Compose the user message
        parts = []
        if header:
            parts.append(header)
        parts.append(f"Context:\n{context}")
        if history_section:
            parts.append(history_section.rstrip())
        parts.append(f"Question: {query}")
        user = "\n\n".join(parts)

        logger.info(
            "ChatAgent.answer: query=%r, chunks=%d, history_msgs=%d",
            query[:80],
            len(chunks),
            len(history) if history else 0,
        )

        return self._call(_SYSTEM, user)
