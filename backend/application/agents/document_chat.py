"""Document chat agent for AI-assisted Q&A about document content."""

import logging

from application.agents._tokens import count_tokens, truncate_tokens
from application.agents.base import BaseAgent
from core.exceptions import RateLimitError
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)

_CONTEXT_MAX_TOKENS = 4000
_HISTORY_MAX_TOKENS = 2000

_BASE_SYSTEM = (
    "You are a helpful document assistant. Answer the user's questions based on the "
    "document context provided in the Background section. Be concise and accurate. "
    "If the answer cannot be found in the provided context, say so clearly. "
    "Format your responses using markdown when helpful."
)


class DocumentChatAgent(BaseAgent):
    """Agent that answers questions about a document using its extracted text."""

    def answer(
        self,
        messages: list[dict[str, str]],
        context: str | None = None,
        params: GenerationParams | None = None,
        agent_prompt: str | None = None,
    ) -> str:
        """Answer a user question based on document context and conversation history.

        Args:
            messages: Conversation history, each with 'role' and 'content'.
            context: Extracted text from the document (page window) to ground answers in.
            params: Optional generation parameters (temperature, top_p, max_tokens).
            agent_prompt: Optional agent definition/personality prompt.

        Returns:
            The assistant's reply.
        """
        system = _BASE_SYSTEM
        if agent_prompt:
            system = agent_prompt + "\n\n" + system

        user_question = messages[-1]["content"] if messages else ""
        history = messages[:-1]

        # Build user message: background first, history next, question last
        parts: list[str] = []

        if context and context.strip():
            truncated_ctx = truncate_tokens(context.strip(), _CONTEXT_MAX_TOKENS)
            parts.append(
                "--- Background (reference only) ---\n"
                f"Document excerpt (current pages):\n{truncated_ctx}"
            )

        if history:
            # Trim history from oldest entries until it fits the budget
            while history:
                history_lines = []
                for msg in history:
                    prefix = "User" if msg["role"] == "user" else "Assistant"
                    history_lines.append(f"{prefix}: {msg['content']}")
                history_text = "\n".join(history_lines)
                if count_tokens(history_text) <= _HISTORY_MAX_TOKENS:
                    break
                history = history[1:]

            if history:
                history_lines = []
                for msg in history:
                    prefix = "User" if msg["role"] == "user" else "Assistant"
                    history_lines.append(f"{prefix}: {msg['content']}")
                parts.append(
                    "--- Conversation so far ---\n" + "\n".join(history_lines)
                )

        parts.append(f"--- Latest question ---\n{user_question}")
        user_message = "\n\n".join(parts)

        try:
            return self._call(system, user_message, params=params)
        except RateLimitError:
            raise
        except Exception as e:
            logger.error("Document chat LLM call failed: %s", e)
            return "Sorry, I encountered an error processing your request. Please try again."
