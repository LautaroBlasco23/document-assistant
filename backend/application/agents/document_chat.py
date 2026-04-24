"""Document chat agent for AI-assisted Q&A about document content."""

import logging

from application.agents.base import BaseAgent

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful document assistant. Answer the user's questions based on the "
    "document context provided. Be concise and accurate. If the answer cannot be found "
    "in the document context, say so clearly. Format your responses using markdown when helpful."
)


class DocumentChatAgent(BaseAgent):
    """Agent that answers questions about a document using its extracted text."""

    def answer(self, messages: list[dict[str, str]], context: str | None = None) -> str:
        """Answer a user question based on document context and conversation history.

        Args:
            messages: Conversation history, each with 'role' and 'content'.
            context: Extracted text from the document to ground answers in.

        Returns:
            The assistant's reply.
        """
        system = _DEFAULT_SYSTEM_PROMPT
        if context:
            system += f"\n\nHere is the document context:\n\n{context}"

        user_message = messages[-1]["content"] if messages else ""

        if len(messages) > 1:
            history_parts = []
            for msg in messages[:-1]:
                prefix = "User" if msg["role"] == "user" else "Assistant"
                history_parts.append(f"{prefix}: {msg['content']}")
            history = "\n".join(history_parts)
            user_message = f"Previous conversation:\n{history}\n\nLatest question: {user_message}"

        try:
            return self._call(system, user_message)
        except Exception as e:
            logger.error("Document chat LLM call failed: %s", e)
            return "Sorry, I encountered an error processing your request. Please try again."
