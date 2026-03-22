import json
import logging
from typing import Callable

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_BATCH_SIZE = 4

_SYSTEM = (
    "You are an expert educator creating flashcards for spaced repetition study. "
    "Given text from a book chapter, create flashcards that help the reader memorize "
    "and understand the material.\n\n"
    "Generate EXACTLY 9 flashcards organized in 3 categories (3 cards each):\n\n"
    "### TERMINOLOGY (3 cards)\n"
    "Cards that test definitions, key terms, and vocabulary introduced in the text.\n"
    "- Front: The term or concept name.\n"
    "- Back: A clear, concise definition in 1-2 sentences, using context from the text.\n\n"
    "### KEY FACTS (3 cards)\n"
    "Cards that test specific facts, details, examples, dates, names, or data points.\n"
    "- Front: A specific question about a fact from the text.\n"
    "- Back: The precise answer with relevant details.\n\n"
    "### CONCEPTS (3 cards)\n"
    "Cards that test understanding of relationships, causes, processes, or arguments.\n"
    "- Front: A question about why/how something works or relates to other ideas.\n"
    "- Back: A clear explanation in 2-3 sentences.\n\n"
    "Rules:\n"
    "- Every card MUST be answerable from the provided text alone.\n"
    "- Keep fronts short and precise (one question or term per card).\n"
    "- Keep backs concise but complete — no vague or generic answers.\n"
    "- Do NOT create cards about study exercises, glossary sections, or instructional "
    "material embedded in the text.\n\n"
    "You MUST respond with a JSON object containing a single key 'cards' whose value "
    "is an array of objects with 'front', 'back', and 'category' keys.\n"
    "Valid categories: 'terminology', 'key_facts', 'concepts'\n\n"
    'Example: {"cards": ['
    '{"front": "Photosynthesis", "back": "The process by which plants convert '
    'sunlight into energy...", "category": "terminology"}, '
    '{"front": "What wavelengths of light do chloroplasts absorb most?", '
    '"back": "Red and blue wavelengths...", "category": "key_facts"}, '
    '{"front": "Why do leaves appear green?", '
    '"back": "Because chlorophyll reflects green light...", "category": "concepts"}'
    "]}"
)


class FlashcardGeneratorAgent(BaseAgent):
    def generate(
        self,
        chunks: list[Chunk],
        on_progress: Callable[[int, int, int], None] | None = None,
        chapter_title: str = "",
        document_title: str = "",
        document_description: str = "",
        document_type: str = "",
    ) -> list[dict]:
        """Generate categorized flashcards from chunks.

        Args:
            chunks: List of text chunks to process.
            on_progress: Optional callback called after each batch with
                (batch_number, total_batches, cards_so_far).
            chapter_title: Title of the chapter for context.
            document_title: Title of the document for context.
            document_description: User-provided description of the document for context.
            document_type: Type of document (book, paper, documentation, etc.) for context.
        """
        all_cards = []
        total_batches = (len(chunks) + _BATCH_SIZE - 1) // _BATCH_SIZE

        # Build context header
        header_parts = []
        if document_title:
            header_parts.append(f"Document: {document_title}")
        if chapter_title:
            header_parts.append(f"Chapter: {chapter_title}")
        if document_type:
            header_parts.append(f"Document type: {document_type}")
        if document_description:
            header_parts.append(f"Document context: {document_description}")
        header = "\n".join(header_parts)

        for batch_idx in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[batch_idx : batch_idx + _BATCH_SIZE]
            context = "\n\n".join(
                f"[p.{c.metadata.page_number if c.metadata else '?'}] {c.text}"
                for c in batch
            )
            user = f"{header}\n\nText:\n{context}" if header else f"Text:\n{context}"
            batch_number = batch_idx // _BATCH_SIZE + 1
            logger.info(
                "Processing flashcard batch %d/%d (%d chunks)",
                batch_number,
                total_batches,
                len(batch),
            )
            raw = self._call_json(_SYSTEM, user)
            logger.debug(
                "Batch %d/%d: LLM returned %d chars",
                batch_number,
                total_batches,
                len(raw),
            )
            cards = self._parse(raw)
            all_cards.extend(cards)
            if on_progress:
                on_progress(batch_number, total_batches, len(all_cards))
        logger.info(
            "Generated %d flashcards from %d chunks (%d batches)",
            len(all_cards),
            len(chunks),
            total_batches,
        )
        return all_cards

    @staticmethod
    def _parse(raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse flashcard JSON. Raw (first 500 chars): %s",
                raw[:500],
            )
            return []

        if isinstance(data, dict):
            data = data.get("cards", data.get("flashcards", []))
        if not isinstance(data, list):
            logger.warning(
                "Flashcard response is not a list. Type: %s, raw (first 500 chars): %s",
                type(data).__name__,
                raw[:500],
            )
            return []

        return [
            {
                "front": d.get("front", ""),
                "back": d.get("back", ""),
                "category": d.get("category", "key_facts"),
            }
            for d in data
            if isinstance(d, dict) and "front" in d
        ]
