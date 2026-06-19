"""Document optimizer agent — creates an optimized study document from extracted text."""

import logging

from application.agents.base import BaseAgent
from application.agents.text_preprocessor import detect_and_mark_titles
from application.prompts import OPTIMIZE_DOCUMENT_SYSTEM
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)


class DocumentOptimizerAgent(BaseAgent):
    """Agent that creates an optimized study document with summary and suggested questions."""

    def optimize(
        self,
        text: str,
        params: GenerationParams | None = None,
        agent_prompt: str | None = None,
        max_retries: int = 2,
        context: str | None = None,
    ) -> str:
        """Create an optimized study document from source text.

        Args:
            text: The original document content to optimize.
            params: Optional generation parameters.
            agent_prompt: Optional user-defined agent prompt prepended to the system prompt.
            max_retries: Number of retries on transient failures (empty responses).
            context: Optional overlap context from a previous chunk (for chunked processing).

        Returns:
            The optimized, Markdown-formatted study document.
        """
        base = OPTIMIZE_DOCUMENT_SYSTEM

        # Add context continuation instruction if this is a continuation chunk
        if context:
            base = (
                "CONTINUATION INSTRUCTION: The text below continues from a previous section. "
                f"Previous context (for reference only, do NOT repeat):\n---\n{context}\n---\n\n"
                "Continue optimizing the text naturally from where it left off. "
                "Do not repeat or rephrase the context above. "
                "This is a continuation chunk — do NOT include the '## Suggested Questions' "
                "section here. Only the final chunk should contain it.\n\n" + base
            )

        system = (agent_prompt + "\n\n" + base) if agent_prompt else base

        # Preprocess: mark headings only (no duplicate removal — summarization
        # naturally handles redundancy, and we want to preserve context)
        preprocessed = detect_and_mark_titles(text)

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self._call(system, preprocessed, params=params)
            except ValueError as e:
                if "empty response" in str(e).lower() and attempt < max_retries:
                    logger.warning(
                        "Document optimization attempt %d/%d failed: %s. Retrying...",
                        attempt + 1, max_retries + 1, e
                    )
                    last_error = e
                    continue
                raise
            except Exception as e:
                logger.error("Document optimization LLM call failed: %s", e)
                raise

        raise last_error
