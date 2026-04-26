"""Flashcard generator agent for creating flashcards from text selections."""

import json
import logging
import re
from datetime import datetime
from uuid import uuid4

from application.agents.base import BaseAgent
from core.model.knowledge_tree import Flashcard

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert educator. Create exactly ONE high-quality flashcard "
    "from the excerpt provided by the user.\n\n"
    "Return ONLY a JSON object with exactly two keys:\n"
    '{"front": "...", "back": "..."}\n\n'
    "Rules:\n"
    "- Front should be a concise question or term.\n"
    "- Back should be a precise, complete answer in 1-2 sentences.\n"
    "- Do NOT add markdown code fences.\n"
    "- Do NOT add any text outside the JSON object."
)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    m = _CODE_FENCE_RE.match(stripped)
    return m.group(1).strip() if m else stripped


class FlashcardGeneratorAgent(BaseAgent):
    """Agent that generates a flashcard from a selected text excerpt."""

    def generate(
        self,
        selected_text: str,
        chapter_context: str | None = None,
        agent_prompt: str | None = None,
    ) -> dict[str, str]:
        """Generate a flashcard from the provided text.

        Args:
            selected_text: The text excerpt to base the flashcard on.
            chapter_context: Optional surrounding chapter content used for grounding.
            agent_prompt: Optional agent definition to prepend to system prompt.

        Returns:
            A dict with 'front' and 'back' keys.
        """
        system = _SYSTEM_PROMPT
        if agent_prompt:
            system = agent_prompt + "\n\n" + system
        if chapter_context and chapter_context.strip():
            user_prompt = (
                "CHAPTER CONTEXT (for reference only, do not summarize this):\n"
                f"{chapter_context.strip()}\n\n"
                "FOCUS EXCERPT (build the flashcard from this):\n"
                f"{selected_text}"
            )
        else:
            user_prompt = selected_text
        raw = self._llm.chat(system, user_prompt, format="json")
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
        """Generate and return a Flashcard domain object.

        Args:
            selected_text: The text excerpt to base the flashcard on.
            tree_id: UUID of the knowledge tree.
            chapter_id: UUID of the chapter.

        Returns:
            A Flashcard domain model instance.
        """
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
