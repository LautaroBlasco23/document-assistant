"""Flashcard generator agent for creating flashcards from text selections."""

import json
import logging
import re
from datetime import datetime
from typing import Callable
from uuid import UUID, uuid4

from application.agents._batching import batch_chunks_by_words
from application.agents.base import BaseAgent
from core.model.chunk import Chunk
from core.model.knowledge_tree import Flashcard

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert educator. Create exactly ONE high-quality flashcard "
    "from the FOCUS EXCERPT provided by the user.\n\n"
    "Return ONLY a JSON object with exactly two keys:\n"
    '{"front": "...", "back": "..."}\n\n'
    "Rules:\n"
    "- Front should be a concise question or term.\n"
    "- Back should be a precise, complete answer in 1-2 sentences.\n"
    "- Do NOT add markdown code fences.\n"
    "- Do NOT add any text outside the JSON object."
)

_BATCH_SYSTEM_PROMPT = (
    "You are an expert educator. Create high-quality flashcards from the text provided by the user."
    "\n\nReturn ONLY a JSON object with a single key 'flashcards' containing an array of objects, "
    "each with exactly two keys 'front' and 'back':\n"
    '{"flashcards": [{"front": "...", "back": "..."}, ...]}\n\n'
    "Rules:\n"
    "- Front should be a concise question or term (max 120 characters).\n"
    "- Back should be a precise, complete answer in 1-3 sentences.\n"
    "- Cover the most important concepts, terms, and facts in the text.\n"
    "- Do NOT add markdown code fences.\n"
    "- Do NOT add any text outside the JSON object."
)


def _build_flashcard_user_prompt(
    selected_text: str,
    chapter_context: str | None,
    agent_prompt: str | None,
    book_overview: str | None = None,
) -> str:
    parts = ["--- Background (reference only) ---"]
    if agent_prompt:
        parts.append(f"Agent guidance:\n{agent_prompt}")
    if book_overview:
        parts.append(f"Book overview:\n{book_overview}")
    if chapter_context and chapter_context.strip():
        parts.append(f"Surrounding chapter context:\n{chapter_context.strip()}")
    parts.append("--- Focus ---")
    parts.append(f"Focus excerpt (build the flashcard from this):\n{selected_text}")
    return "\n\n".join(parts)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    m = _CODE_FENCE_RE.match(stripped)
    return m.group(1).strip() if m else stripped


class FlashcardGeneratorAgent(BaseAgent):
    """Agent that generates flashcards from text selections or chapter chunks."""

    _MAX_WORDS_PER_BATCH = 3000

    def generate(
        self,
        selected_text: str,
        chapter_context: str | None = None,
        agent_prompt: str | None = None,
        book_overview: str | None = None,
    ) -> dict[str, str]:
        """Generate a flashcard from the provided text.

        Args:
            selected_text: The text excerpt to base the flashcard on.
            chapter_context: Optional surrounding chapter content used for grounding.
            agent_prompt: Optional agent definition/personality prompt.
            book_overview: Optional overview of the source document.

        Returns:
            A dict with 'front' and 'back' keys.
        """
        user_prompt = _build_flashcard_user_prompt(
            selected_text, chapter_context, agent_prompt, book_overview
        )
        raw = self._llm.chat(_SYSTEM_PROMPT, user_prompt, format="json")
        text = _strip_code_fences(raw)
        data = json.loads(text)
        return {
            "front": str(data["front"]).strip(),
            "back": str(data["back"]).strip(),
        }

    def create_flashcard(
        self,
        selected_text: str,
        tree_id: str,
        chapter_id: str,
        chapter_context: str | None = None,
    ) -> Flashcard:
        """Generate and return a Flashcard domain object from a selection."""
        result = self.generate(selected_text, chapter_context=chapter_context)
        return Flashcard(
            id=uuid4(),
            tree_id=tree_id,
            chapter_id=chapter_id,
            doc_id=None,
            front=result["front"],
            back=result["back"],
            source_text=selected_text,
            created_at=datetime.now(),
        )

    def generate_batch(
        self,
        chunks: list[Chunk],
        tree_id: UUID,
        chapter_id: UUID,
        num_flashcards: int | None = None,
        agent_prompt: str | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Flashcard]:
        """Generate multiple flashcards from chapter chunks.

        Args:
            chunks: Text chunks from the chapter.
            tree_id: UUID of the knowledge tree.
            chapter_id: UUID of the chapter.
            num_flashcards: Desired number per batch. None = model chooses.
            agent_prompt: Optional agent system prompt override.
            on_progress: Called with (batch_i, total_batches) after each batch.

        Returns:
            List of Flashcard domain objects.
        """
        text_batches = batch_chunks_by_words(chunks, self._MAX_WORDS_PER_BATCH)
        if not text_batches:
            return []

        total_batches = len(text_batches)
        system_prompt = _BATCH_SYSTEM_PROMPT
        if agent_prompt:
            system_prompt = agent_prompt + "\n\n" + system_prompt

        num_hint = f" Generate approximately {num_flashcards} flashcards." if num_flashcards else ""
        all_flashcards: list[Flashcard] = []

        for batch_i, batch_text in enumerate(text_batches, 1):
            logger.info("Generating flashcards: batch %d/%d", batch_i, total_batches)
            user_prompt = batch_text + num_hint
            raw = self._call_json_with_retry(system_prompt, user_prompt)

            try:
                parsed = json.loads(raw)
                items = parsed.get("flashcards", [])
                if not isinstance(items, list):
                    items = []
            except (json.JSONDecodeError, ValueError):
                logger.warning("Could not parse flashcard batch %d/%d", batch_i, total_batches)
                items = []

            for item in items:
                front = str(item.get("front", "")).strip()
                back = str(item.get("back", "")).strip()
                if front and back:
                    all_flashcards.append(
                        Flashcard(
                            id=uuid4(),
                            tree_id=tree_id,
                            chapter_id=chapter_id,
                            doc_id=None,
                            front=front,
                            back=back,
                            source_text=None,
                            created_at=datetime.now(),
                        )
                    )

            if on_progress:
                on_progress(batch_i, total_batches)

        return all_flashcards
