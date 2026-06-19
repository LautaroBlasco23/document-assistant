"""Text improvement agent — rewrites document content with better style and Markdown formatting."""

import logging

from application.agents.base import BaseAgent
from application.agents.text_preprocessor import preprocess_for_improvement
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)

_SYSTEM_FORMATTING = (
    "You are a Markdown formatting validator. Your task is to FIX broken Markdown "
    "formatting in the provided text. Do NOT rewrite, rephrase, or alter any text "
    "content — only fix structural Markdown issues.\n\n"
    "STRUCTURAL MARKERS in the input (already identified for you):\n"
    "- __HEADING__...__END_HEADING__ → convert to ## Heading\n"
    "- __SUBHEADING__...__END_SUBHEADING__ → convert to ### Subheading\n\n"
    "ONLY fix these issues:\n"
    "- Headings without blank lines after them → add a blank line\n"
    "- Headings missing # markers (detected via __HEADING__ markers) → add ## prefix\n"
    "- Subheadings (__SUBHEADING__ markers) → add ### prefix\n"
    "- Lists with broken markers → fix - or 1. prefixes\n"
    "- Tables with broken pipe formatting → fix | alignment\n"
    "- Paragraphs running together without blank line separation → add blank line\n"
    "- Broken inline formatting (unclosed ** or *) → close them\n\n"
    "DO NOT:\n"
    "- Rewrite, rephrase, or reword any sentence\n"
    "- Add italic/bold for emphasis that wasn't in the original\n"
    "- Add new headings, sections, or structure\n"
    "- Remove any content (duplicate paragraphs are already removed before you see the text)\n"
    "- Change word order, vocabulary, or sentence structure\n\n"
    "Image references (![](...)) → preserve exactly as-is.\n"
    "Return ONLY the text with fixed Markdown formatting, no preamble or explanation."
)


class TextImprovementAgent(BaseAgent):
    """Agent that improves document text style and applies Markdown formatting."""

    def improve(
        self,
        text: str,
        params: GenerationParams | None = None,
        agent_prompt: str | None = None,
        max_retries: int = 2,
        context: str | None = None,
    ) -> str:
        """Fix Markdown formatting in the provided text.

        Args:
            text: The original document content to format.
            params: Optional generation parameters.
            agent_prompt: Optional user-defined agent prompt prepended to the system prompt.
            max_retries: Number of retries on transient failures (empty responses).
            context: Optional overlap context from a previous chunk (for chunked processing).

        Returns:
            The formatted text with fixed Markdown.
        """
        base = _SYSTEM_FORMATTING

        # Add context continuation instruction if this is a continuation chunk
        if context:
            base = (
                "CONTINUATION INSTRUCTION: The text below continues from a previous section. "
                f"Previous context (for reference only, do NOT repeat):\n---\n{context}\n---\n\n"
                "Continue improving the text naturally from where it left off. "
                "Do not repeat or rephrase the context above.\n\n" + base
            )

        system = (agent_prompt + "\n\n" + base) if agent_prompt else base
        preprocessed = preprocess_for_improvement(text)

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self._call(system, preprocessed, params=params)
            except ValueError as e:
                # Retry on empty response errors (transient LLM issues)
                if "empty response" in str(e).lower() and attempt < max_retries:
                    logger.warning(
                        "Text improvement attempt %d/%d failed: %s. Retrying...",
                        attempt + 1, max_retries + 1, e
                    )
                    last_error = e
                    continue
                raise
            except Exception as e:
                logger.error("Text improvement LLM call failed: %s", e)
                raise

        # Should not reach here, but just in case
        raise last_error
