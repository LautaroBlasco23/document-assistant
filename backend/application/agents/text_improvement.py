"""Text improvement agent — rewrites document content with better style and Markdown formatting."""

import logging

from application.agents.base import BaseAgent
from application.agents.text_preprocessor import preprocess_for_improvement
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a professional writing assistant for books (fiction and non-fiction). "
    "Your task is to rewrite the provided text to improve its clarity, style, and structure. "
    "Apply clean Markdown formatting.\n\n"
    "TEXT TYPE RULES:\n"
    "- Chapter titles and section names → ## or ### headings\n"
    "- Dialogue → keep as regular paragraphs with proper quotation marks\n"
    "- Narrative prose → regular paragraphs, apply italic/bold for emphasis where natural\n"
    "- Image references (![](...)) → preserve exactly as-is\n"
    "- Lists → detect and format with - or 1. 2. 3. as appropriate\n\n"
    "STRUCTURAL MARKERS in the input:\n"
    "- __HEADING__...__END_HEADING__ → convert to ## Heading\n"
    "- __SUBHEADING__...__END_SUBHEADING__ → convert to ### Subheading\n\n"
    "Preserve all factual content and meaning — do not add, remove, or change any "
    "information (except exact duplicate paragraphs, which should be removed). "
    "Return ONLY the improved text, with no preamble, no explanation, and no surrounding "
    "commentary."
)

_SYSTEM_FORMATTING = (
    "You are a professional document formatter for books (fiction and non-fiction). "
    "Your task is to rewrite the provided text to apply clean Markdown formatting for "
    "improved readability.\n\n"
    "STRUCTURAL MARKERS in the input:\n"
    "- __HEADING__...__END_HEADING__ → convert to ## Heading\n"
    "- __SUBHEADING__...__END_SUBHEADING__ → convert to ### Subheading\n\n"
    "TEXT TYPE RULES:\n"
    "- Chapter titles and section names → ## or ### headings (use markers as guidance)\n"
    "- Dialogue → keep as regular paragraphs with proper quotation marks\n"
    "- Narrative prose → regular paragraphs, apply italic/bold for emphasis where natural\n"
    "- Image references (![](...)) → preserve exactly as-is\n"
    "- Lists → detect and format with - or 1. 2. 3. as appropriate\n\n"
    "DUPLICATE REMOVAL: Remove any exact duplicate paragraphs that remain from PDF "
    "extraction artifacts.\n\n"
    "Preserve ALL factual content and meaning — do not add, remove, or rephrase any "
    "information (except exact duplicate paragraphs as noted above). "
    "Return ONLY the reformatted text, with no preamble, no explanation, and no "
    "surrounding commentary."
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
        preprocessed = preprocess_for_improvement(text)
        try:
            return self._call(system, preprocessed, params=params)
        except Exception as e:
            logger.error("Text improvement LLM call failed: %s", e)
            raise
