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

_SYSTEM_FORMATTING = (
    "You are a professional document formatter. Your task is to rewrite the provided text "
    "to apply clean Markdown formatting for improved readability. Detect and apply: "
    "headings (##, ###) for titles and sections, bullet lists (-) for unordered items, "
    "numbered lists (1., 2.) for ordered items, bold (**text**) for emphasis, "
    "italic (*text*) for subtle emphasis, and code blocks (```) for technical content. "
    "Preserve ALL factual content and meaning exactly — do not add, remove, rephrase, "
    "or change any information. Return ONLY the reformatted text, with no preamble, "
    "no explanation, and no surrounding commentary."
)


class TextImprovementAgent(BaseAgent):
    """Agent that improves document text style and applies Markdown formatting."""

    def improve(
        self,
        text: str,
        params: GenerationParams | None = None,
        agent_prompt: str | None = None,
        mode: str = "text",
    ) -> str:
        """Rewrite text with improved style and Markdown formatting.

        Args:
            text: The original document content to improve.
            params: Optional generation parameters.
            agent_prompt: Optional user-defined agent prompt prepended to the system prompt.
            mode: "text" to rewrite content, "formatting" to only apply Markdown structure.

        Returns:
            The improved, Markdown-formatted text.
        """
        base = _SYSTEM_FORMATTING if mode == "formatting" else _SYSTEM
        system = (agent_prompt + "\n\n" + base) if agent_prompt else base
        try:
            return self._call(system, text, params=params)
        except Exception as e:
            logger.error("Text improvement LLM call failed: %s", e)
            raise
