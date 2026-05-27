"""Text improvement agent — rewrites document content with better style and Markdown formatting."""

import logging

from application.agents.base import BaseAgent
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a professional writing assistant. Your task is to rewrite the provided text "
    "to improve its clarity, style, and structure. Apply clean Markdown formatting: use "
    "headings (##, ###), bullet lists, numbered lists, bold/italic emphasis, and code "
    "blocks where appropriate. Preserve all factual content and meaning — do not add, "
    "remove, or change any information. Return ONLY the improved text, with no preamble, "
    "no explanation, and no surrounding commentary."
)


class TextImprovementAgent(BaseAgent):
    """Agent that improves document text style and applies Markdown formatting."""

    def improve(
        self,
        text: str,
        params: GenerationParams | None = None,
        agent_prompt: str | None = None,
    ) -> str:
        """Rewrite text with improved style and Markdown formatting.

        Args:
            text: The original document content to improve.
            params: Optional generation parameters.
            agent_prompt: Optional user-defined agent prompt prepended to the system prompt.

        Returns:
            The improved, Markdown-formatted text.
        """
        system = (agent_prompt + "\n\n" + _SYSTEM) if agent_prompt else _SYSTEM
        try:
            return self._call(system, text, params=params)
        except Exception as e:
            logger.error("Text improvement LLM call failed: %s", e)
            raise
