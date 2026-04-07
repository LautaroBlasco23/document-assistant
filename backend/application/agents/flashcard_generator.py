import json
import logging
import re
from typing import Callable

from application.agents.base import BaseAgent
from application.prompts import FLASHCARDS_SYSTEM
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_MAX_WORDS_PER_BATCH = 3000  # Increased from 2500; main model supports 128k context

_TRIVIAL_PATTERNS = [
    r"^what is (a |an |the )?chapter",
    r"^what is (a |an |the )?book",
    r"^who is the (author|reader|student)",
    r"^what is the title",
    r"^what page",
    r"^how many (pages|chapters|sections)",
    r"^(true or false|yes or no)",
    r"^what (does|did) the (text|passage|chapter|author) (say|state|mention|describe)",
    r"^(according to|as stated in) the (text|passage|chapter)",
    r"^(define|describe|explain|list) \w+$",
]




def _batch_chunks_list(chunks: list[Chunk], max_words: int) -> list[list[Chunk]]:
    """Group chunks into batches that stay within max_words, preserving chunk objects."""
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


def _jaccard_words(a: str, b: str) -> float:
    """Return Jaccard similarity between word sets of two strings."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


class FlashcardGeneratorAgent(BaseAgent):
    def generate(
        self,
        chunks: list[Chunk],
        on_progress: Callable[[int, int, int], None] | None = None,
        chapter_title: str = "",
        document_title: str = "",
        document_description: str = "",
        document_type: str = "",
        chapter_summary: str = "",
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
            chapter_summary: Optional summary of the chapter to help prioritize concepts.
        """
        all_cards = []
        batches = _batch_chunks_list(chunks, _MAX_WORDS_PER_BATCH)
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

        # Build summary block once; prepended to every batch user message
        summary_block = ""
        if chapter_summary:
            summary_block = (
                "Chapter summary (use this to understand what matters most -- "
                "do NOT create cards about the summary itself):\n"
                f"{chapter_summary}\n\n"
            )

        for batch_number, batch in enumerate(batches, 1):
            context = "\n\n".join(
                f"[p.{c.metadata.page_number if c.metadata else '?'}] {c.text}" for c in batch
            )
            if summary_block or header:
                user = f"{summary_block}{header}\n\nText:\n{context}"
            else:
                user = f"Text:\n{context}"

            # Append content density hint to help the model calibrate card count
            word_count = sum(len(c.text.split()) for c in batch)
            user += f"\n\n[Content density: {word_count} words across {len(batch)} text segments]"

            logger.info(
                "Processing flashcard batch %d/%d (%d chunks)",
                batch_number,
                total_batches,
                len(batch),
            )
            raw = self._call_json_with_retry(FLASHCARDS_SYSTEM, user)
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

        # Exact dedup by normalized front
        seen = set()
        unique_cards = []
        for card in all_cards:
            front_normalized = card["front"].strip().lower()
            if front_normalized not in seen:
                seen.add(front_normalized)
                unique_cards.append(card)
        all_cards = unique_cards

        # Near-duplicate dedup by Jaccard similarity on front text
        deduped = []
        for card in all_cards:
            dominated = any(
                _jaccard_words(card["front"], existing["front"]) > 0.8
                for existing in deduped
            )
            if not dominated:
                deduped.append(card)
            else:
                logger.debug("Filtered near-duplicate: %s", card["front"][:80])
        all_cards = deduped

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

            # Skip cards where back adds minimal new information over the front
            front_words = set(front.split()) - {
                "what", "is", "the", "a", "an", "how", "why", "does", "do"
            }
            back_words_set = set(back.lower().split())
            if front_words and len(front_words) <= 4:
                new_words = back_words_set - front_words - {
                    "is", "a", "an", "the", "that", "which", "are", "was"
                }
                if len(new_words) < 3:
                    logger.debug("Filtered card (back restates front): %s", front[:80])
                    continue

            filtered.append(card)

        removed = len(cards) - len(filtered)
        if removed:
            logger.info("Quality filter removed %d/%d cards", removed, len(cards))
        return filtered
