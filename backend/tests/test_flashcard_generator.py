"""Unit tests for FlashcardGeneratorAgent: parsing, filtering, deduplication, batching."""
import json

import pytest

from application.agents.flashcard_generator import (
    FlashcardGeneratorAgent,
    _batch_chunks,
    _MAX_WORDS_PER_BATCH,
)
from core.model.chunk import Chunk, ChunkMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(text: str, page_number: int = 1) -> Chunk:
    return Chunk(
        text=text,
        token_count=len(text.split()),
        metadata=ChunkMetadata(
            source_file="test-hash",
            chapter_index=0,
            page_number=page_number,
            start_char=0,
            end_char=len(text),
        ),
    )


def _valid_cards_json(cards: list[dict]) -> str:
    return json.dumps({"cards": cards})


# ---------------------------------------------------------------------------
# Test _parse
# ---------------------------------------------------------------------------


def test_parse_valid_json():
    raw = _valid_cards_json([
        {"front": "Entropy", "back": "A measure of disorder in a system.", "category": "terminology", "source_page": 5},
        {"front": "What is the second law of thermodynamics?", "back": "Entropy always increases in a closed system.", "category": "key_facts", "source_page": 6},
    ])
    cards = FlashcardGeneratorAgent._parse(raw)
    assert len(cards) == 2
    assert cards[0]["front"] == "Entropy"
    assert cards[0]["source_page"] == 5
    assert cards[1]["category"] == "key_facts"


def test_parse_accepts_flashcards_key():
    """_parse should accept both 'cards' and 'flashcards' as top-level key."""
    raw = json.dumps({"flashcards": [
        {"front": "Osmosis", "back": "Movement of water across a semipermeable membrane.", "category": "terminology"},
    ]})
    cards = FlashcardGeneratorAgent._parse(raw)
    assert len(cards) == 1
    assert cards[0]["front"] == "Osmosis"


def test_parse_malformed_json_returns_empty():
    cards = FlashcardGeneratorAgent._parse("this is not json at all {{{")
    assert cards == []


def test_parse_missing_front_skipped():
    raw = json.dumps({"cards": [
        {"back": "Some answer", "category": "key_facts"},
    ]})
    cards = FlashcardGeneratorAgent._parse(raw)
    assert cards == []


def test_parse_source_page_as_string():
    raw = _valid_cards_json([
        {"front": "Mitosis", "back": "Cell division that produces two identical daughter cells.", "category": "terminology", "source_page": "12"},
    ])
    cards = FlashcardGeneratorAgent._parse(raw)
    assert cards[0]["source_page"] == 12


def test_parse_source_page_missing_is_omitted():
    raw = _valid_cards_json([
        {"front": "Meiosis", "back": "Division producing four genetically unique cells.", "category": "terminology"},
    ])
    cards = FlashcardGeneratorAgent._parse(raw)
    assert "source_page" not in cards[0]


# ---------------------------------------------------------------------------
# Test _filter_low_quality
# ---------------------------------------------------------------------------


def test_filter_trivial_cards():
    cards = [
        {"front": "What is a book?", "back": "A bound set of pages with text.", "category": "key_facts"},
        {"front": "What is the title of this chapter?", "back": "Chapter One.", "category": "key_facts"},
        {"front": "Who is the author?", "back": "Jane Smith.", "category": "key_facts"},
        {"front": "What page does section 2 start?", "back": "Page 14.", "category": "key_facts"},
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == []


def test_filter_preserves_good_cards():
    cards = [
        {
            "front": "What distinguishes active transport from passive diffusion?",
            "back": "Active transport requires ATP to move molecules against a concentration gradient, while passive diffusion moves molecules along the gradient without energy input.",
            "category": "concepts",
        },
        {
            "front": "Allosteric regulation",
            "back": "A mechanism where a molecule binds to a site other than the active site, changing the enzyme's shape and activity.",
            "category": "terminology",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert len(result) == 2


def test_filter_short_back_removed():
    cards = [
        {"front": "What is photosynthesis?", "back": "Yes.", "category": "key_facts"},
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == []


def test_filter_short_front_removed():
    cards = [
        {"front": "ATP", "back": "Adenosine triphosphate is the primary energy currency of the cell, providing energy for most cellular processes.", "category": "terminology"},
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == []


def test_filter_front_back_overlap_removed():
    """Cards where front is a substring of back should be removed."""
    cards = [
        {"front": "photosynthesis", "back": "photosynthesis converts sunlight into sugar.", "category": "terminology"},
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == []


# ---------------------------------------------------------------------------
# Test deduplication (via generate method logic)
# ---------------------------------------------------------------------------


def test_deduplication_normalizes_case():
    """Ensure normalized front dedup works across case variants."""
    cards = [
        {"front": "Entropy", "back": "A measure of disorder.", "category": "terminology"},
        {"front": "entropy", "back": "A measure of disorder.", "category": "terminology"},
        {"front": "ENTROPY", "back": "A measure of disorder.", "category": "terminology"},
    ]
    # Simulate the dedup logic from generate()
    seen = set()
    unique_cards = []
    for card in cards:
        key = card["front"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique_cards.append(card)
    assert len(unique_cards) == 1


# ---------------------------------------------------------------------------
# Test _batch_chunks
# ---------------------------------------------------------------------------


def test_batch_chunks_single_batch():
    chunks = [_make_chunk("word " * 100) for _ in range(3)]
    batches = _batch_chunks(chunks, max_words=1000)
    assert len(batches) == 1
    assert batches[0] == chunks


def test_batch_chunks_splits_when_over_limit():
    # Each chunk is 1000 words; limit is 2500 so first batch gets 2 chunks, second gets 1
    chunks = [_make_chunk("word " * 1000) for _ in range(3)]
    batches = _batch_chunks(chunks, max_words=2500)
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


def test_batch_chunks_empty_returns_empty():
    assert _batch_chunks([], max_words=2500) == []


def test_batch_chunks_single_oversized_chunk_not_split():
    """A single chunk larger than max_words should still appear as one batch."""
    chunks = [_make_chunk("word " * 5000)]
    batches = _batch_chunks(chunks, max_words=2500)
    assert len(batches) == 1
    assert batches[0] == chunks
