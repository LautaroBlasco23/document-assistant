import json
import logging
import re
from typing import Callable

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_MAX_WORDS_PER_BATCH = 2500  # Conservative to leave room for system prompt + response

_TRIVIAL_PATTERNS = [
    r"^what is (a |an |the )?chapter",
    r"^what is (a |an |the )?book",
    r"^who is the (author|reader|student)",
    r"^what is the title",
    r"^what page",
    r"^how many (pages|chapters|sections)",
    r"^(true or false|yes or no)",
]


def _batch_chunks(chunks: list[Chunk], max_words: int) -> list[list[Chunk]]:
    """Group chunks into batches that stay within max_words."""
    batches: list[list[Chunk]] = []
    current: list[Chunk] = []
    current_words = 0
    for chunk in chunks:
        chunk_words = len(chunk.text.split())
        if current and current_words + chunk_words > max_words:
            batches.append(current)
            current = []
            current_words = 0
        current.append(chunk)
        current_words += chunk_words
    if current:
        batches.append(current)
    return batches

_SYSTEM = (
    "You are an expert educator creating flashcards for spaced repetition study.\n\n"
    "Your goal is to create flashcards that test UNDERSTANDING, not trivial recall. "
    "Every card must be worth a student's time to study.\n\n"
    "QUALITY RULES (follow strictly):\n"
    "- SKIP: metadata, page numbers, chapter references, author names (unless the "
    "author's identity is the subject matter), publication dates, section headings, "
    "table of contents information, and any boilerplate text.\n"
    "- SKIP: facts that are obvious, self-evident, or could be answered without "
    "reading the text (e.g., 'What is a book?' or 'Who is the reader?').\n"
    "- FOCUS: concepts that require understanding to answer correctly. A good test: "
    "if a student could answer the question by guessing or common sense alone, "
    "the card is too easy.\n"
    "- Each card should test a SINGLE idea. Do not combine multiple concepts.\n"
    "- Backs should be precise and complete, not vague summaries.\n\n"
    "Generate EXACTLY 9 flashcards in 3 categories (3 each):\n\n"
    "### TERMINOLOGY (3 cards)\n"
    "Test definitions of domain-specific terms introduced in the text. "
    "Do NOT include everyday words or terms the reader would already know.\n"
    "- Front: The technical term or concept name.\n"
    "- Back: A precise definition in 1-2 sentences using context from the text. "
    "Include an example if the text provides one.\n\n"
    "### KEY FACTS (3 cards)\n"
    "Test specific, non-obvious facts that a reader needs to remember. "
    "Focus on facts that are surprising, counterintuitive, or essential to the argument.\n"
    "- Front: A specific question that cannot be answered by common knowledge.\n"
    "- Back: The precise answer with supporting detail from the text.\n\n"
    "### CONCEPTS (3 cards)\n"
    "Test understanding of relationships, causes, processes, or arguments. "
    "These should require analysis or synthesis, not just recall.\n"
    "- Front: A 'why' or 'how' question about a process, relationship, or argument.\n"
    "- Back: A clear explanation in 2-3 sentences that demonstrates understanding.\n\n"
    "SELF-CHECK before including each card:\n"
    "1. Would a student who skimmed the chapter already know this? If yes, skip it.\n"
    "2. Is this testing understanding or just recognition? Prefer understanding.\n"
    "3. Is the answer specific to this text, or generic knowledge? Prefer text-specific.\n\n"
    "Rules:\n"
    "- Every card MUST be answerable from the provided text alone.\n"
    "- Keep fronts short and precise (one question or term per card).\n"
    "- Keep backs concise but complete.\n"
    "- Do NOT create cards about study exercises, glossary sections, or instructional "
    "material embedded in the text.\n\n"
    'Respond with a JSON object: {"cards": [{"front": ..., "back": ..., '
    '"category": ..., "source_page": ...}]}\n'
    'Valid categories: "terminology", "key_facts", "concepts"\n'
    "For source_page: use the page number from the [p.N] prefix. If unknown, omit."
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
        batches = _batch_chunks(chunks, _MAX_WORDS_PER_BATCH)
        total_batches = len(batches)

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

        for batch_number, batch in enumerate(batches, 1):
            context = "\n\n".join(
                f"[p.{c.metadata.page_number if c.metadata else '?'}] {c.text}" for c in batch
            )
            user = f"{header}\n\nText:\n{context}" if header else f"Text:\n{context}"
            logger.info(
                "Processing flashcard batch %d/%d (%d chunks)",
                batch_number,
                total_batches,
                len(batch),
            )
            raw = self._call_json_with_retry(_SYSTEM, user)
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

        seen = set()
        unique_cards = []
        for card in all_cards:
            front_normalized = card["front"].strip().lower()
            if front_normalized not in seen:
                seen.add(front_normalized)
                unique_cards.append(card)
        all_cards = unique_cards

        all_cards = self._filter_low_quality(all_cards)

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

        cards = []
        for d in data:
            if not isinstance(d, dict) or "front" not in d:
                continue
            card: dict = {
                "front": d.get("front", ""),
                "back": d.get("back", ""),
                "category": d.get("category", "key_facts"),
            }
            raw_page = d.get("source_page")
            if isinstance(raw_page, int):
                card["source_page"] = raw_page
            elif isinstance(raw_page, str):
                try:
                    card["source_page"] = int(raw_page)
                except ValueError:
                    pass
            cards.append(card)
        return cards

    @staticmethod
    def _filter_low_quality(cards: list[dict]) -> list[dict]:
        """Remove flashcards that match common trivial patterns."""
        filtered = []
        for card in cards:
            front = card.get("front", "").strip().lower()
            back = card.get("back", "").strip()

            # Skip cards with very short answers (likely incomplete)
            if len(back.split()) < 3:
                logger.debug("Filtered card (short back): %s", front[:80])
                continue

            # Skip cards with very short questions
            if len(front.split()) < 2:
                logger.debug("Filtered card (short front): %s", front[:80])
                continue

            # Skip cards matching trivial patterns
            is_trivial = False
            for pattern in _TRIVIAL_PATTERNS:
                if re.search(pattern, front):
                    logger.debug("Filtered card (trivial pattern): %s", front[:80])
                    is_trivial = True
                    break
            if is_trivial:
                continue

            # Skip cards where front and back are nearly identical
            if front in back.strip().lower() or back.strip().lower() in front:
                logger.debug("Filtered card (front/back overlap): %s", front[:80])
                continue

            filtered.append(card)

        removed = len(cards) - len(filtered)
        if removed:
            logger.info("Quality filter removed %d/%d cards", removed, len(cards))
        return filtered
