"""Unit tests for FlashcardGeneratorAgent: parsing, filtering, deduplication, batching."""
import json
from unittest.mock import MagicMock

from application.agents.flashcard_generator import (
    FlashcardGeneratorAgent,
    _batch_chunks,
    _jaccard_words,
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
        {
            "front": "Entropy",
            "back": "A measure of disorder in a system.",
            "category": "terminology",
            "source_page": 5,
        },
        {
            "front": "What is the second law of thermodynamics?",
            "back": "Entropy always increases in a closed system.",
            "category": "key_facts",
            "source_page": 6,
        },
    ])
    cards = FlashcardGeneratorAgent._parse(raw)
    assert len(cards) == 2
    assert cards[0]["front"] == "Entropy"
    assert cards[0]["source_page"] == 5
    assert cards[1]["category"] == "key_facts"


def test_parse_accepts_flashcards_key():
    """_parse should accept both 'cards' and 'flashcards' as top-level key."""
    raw = json.dumps({"flashcards": [
        {
            "front": "Osmosis",
            "back": "Movement of water across a semipermeable membrane.",
            "category": "terminology",
        },
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
        {
            "front": "Mitosis",
            "back": "Cell division that produces two identical daughter cells.",
            "category": "terminology",
            "source_page": "12",
        },
    ])
    cards = FlashcardGeneratorAgent._parse(raw)
    assert cards[0]["source_page"] == 12


def test_parse_source_page_missing_is_omitted():
    raw = _valid_cards_json([
        {
            "front": "Meiosis",
            "back": "Division producing four genetically unique cells.",
            "category": "terminology",
        },
    ])
    cards = FlashcardGeneratorAgent._parse(raw)
    assert "source_page" not in cards[0]


# ---------------------------------------------------------------------------
# Test _filter_low_quality
# ---------------------------------------------------------------------------


def test_filter_trivial_cards():
    cards = [
        {"front": "What is a book?", "back": "A bound set of pages.", "category": "key_facts"},
        {
            "front": "What is the title of this chapter?",
            "back": "Chapter One.",
            "category": "key_facts",
        },
        {"front": "Who is the author?", "back": "Jane Smith.", "category": "key_facts"},
        {"front": "What page does section 2 start?", "back": "Page 14.", "category": "key_facts"},
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == []


def test_filter_preserves_good_cards():
    cards = [
        {
            "front": "What distinguishes active transport from passive diffusion?",
            "back": (
                "Active transport requires ATP to move molecules against a concentration"
                " gradient, while passive diffusion moves molecules along the gradient"
                " without energy input."
            ),
            "category": "concepts",
        },
        {
            "front": "Allosteric regulation",
            "back": (
                "A mechanism where a molecule binds to a site other than the active site,"
                " changing the enzyme's shape and activity."
            ),
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
        {
            "front": "ATP",
            "back": (
                "Adenosine triphosphate is the primary energy currency of the cell,"
                " providing energy for most cellular processes."
            ),
            "category": "terminology",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == []


def test_filter_front_back_overlap_removed():
    """Cards where front is a substring of back should be removed."""
    cards = [
        {
            "front": "photosynthesis",
            "back": "photosynthesis converts sunlight into sugar.",
            "category": "terminology",
        },
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


# ---------------------------------------------------------------------------
# Test _jaccard_words
# ---------------------------------------------------------------------------


def test_jaccard_identical_strings():
    assert _jaccard_words("foo bar baz", "foo bar baz") == 1.0


def test_jaccard_no_overlap():
    assert _jaccard_words("foo bar", "baz qux") == 0.0


def test_jaccard_partial_overlap():
    score = _jaccard_words("what is entropy", "what is photosynthesis")
    assert 0.0 < score < 1.0


def test_jaccard_empty_string():
    assert _jaccard_words("", "foo bar") == 0.0
    assert _jaccard_words("foo bar", "") == 0.0


# ---------------------------------------------------------------------------
# Test variable card count parsing
# ---------------------------------------------------------------------------


def test_variable_card_count_parsing_3_cards():
    cards_data = [
        {"front": f"Question {i}", "back": f"Answer {i} with detail.", "category": "key_facts"}
        for i in range(3)
    ]
    result = FlashcardGeneratorAgent._parse(_valid_cards_json(cards_data))
    assert len(result) == 3


def test_variable_card_count_parsing_7_cards():
    cards_data = [
        {"front": f"Question {i}", "back": f"Answer {i} with detail.", "category": "key_facts"}
        for i in range(7)
    ]
    result = FlashcardGeneratorAgent._parse(_valid_cards_json(cards_data))
    assert len(result) == 7


def test_variable_card_count_parsing_12_cards():
    cards_data = [
        {"front": f"Question {i}", "back": f"Answer {i} with detail.", "category": "terminology"}
        for i in range(12)
    ]
    result = FlashcardGeneratorAgent._parse(_valid_cards_json(cards_data))
    assert len(result) == 12


# ---------------------------------------------------------------------------
# Test new trivial patterns
# ---------------------------------------------------------------------------


def test_filter_meta_referential():
    """Cards that ask what the text/passage/chapter says should be filtered."""
    cards = [
        {
            "front": "What does the text say about metabolism?",
            "back": "The text explains that metabolism includes anabolism and catabolism.",
            "category": "key_facts",
        },
        {
            "front": "What did the author describe about cell division?",
            "back": "The author described mitosis and meiosis as two distinct processes.",
            "category": "key_facts",
        },
        {
            "front": "According to the chapter, what is entropy?",
            "back": "According to the chapter, entropy is a measure of disorder.",
            "category": "key_facts",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == [], f"Expected all meta-referential cards filtered, got: {result}"


def test_filter_vague_define():
    """Cards with 'Define X' (single word target) should be filtered."""
    cards = [
        {
            "front": "Define entropy",
            "back": "Entropy is a measure of disorder or randomness within a thermodynamic system.",
            "category": "terminology",
        },
        {
            "front": "Explain photosynthesis",
            "back": "Photosynthesis is the process by which plants convert sunlight into glucose.",
            "category": "concepts",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == [], f"Expected vague define/explain cards filtered, got: {result}"


def test_filter_vague_define_multi_word_not_filtered():
    """Multi-word 'Define X Y' should NOT be filtered by the single-word pattern."""
    cards = [
        {
            "front": "Define active transport mechanism",
            "back": (
                "Active transport is the movement of molecules against a concentration"
                " gradient using ATP energy."
            ),
            "category": "terminology",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert len(result) == 1, "Multi-word define should not be filtered"


# ---------------------------------------------------------------------------
# Test near-duplicate Jaccard dedup
# ---------------------------------------------------------------------------


def test_near_duplicate_jaccard():
    """Cards with >0.8 word overlap in fronts should be deduplicated."""
    cards = [
        {
            "front": "What is the role of ATP in cellular respiration?",
            "back": "ATP provides energy for metabolic processes in the cell through hydrolysis.",
            "category": "key_facts",
        },
        {
            "front": "What is the role of ATP in the cellular respiration?",
            "back": "ATP supplies energy needed by cells during cellular respiration.",
            "category": "key_facts",
        },
    ]
    # Simulate the dedup logic from generate()
    deduped = []
    for card in cards:
        dominated = any(
            _jaccard_words(card["front"], existing["front"]) > 0.8
            for existing in deduped
        )
        if not dominated:
            deduped.append(card)
    assert len(deduped) == 1, "Near-duplicate fronts should be deduplicated to 1"


def test_near_duplicate_different_fronts_kept():
    """Cards with sufficiently different fronts should both be kept."""
    cards = [
        {
            "front": "What is photosynthesis?",
            "back": "Photosynthesis is the conversion of sunlight into glucose by plants.",
            "category": "terminology",
        },
        {
            "front": "What is cellular respiration?",
            "back": "Cellular respiration is the breakdown of glucose to produce ATP energy.",
            "category": "terminology",
        },
    ]
    deduped = []
    for card in cards:
        dominated = any(
            _jaccard_words(card["front"], existing["front"]) > 0.8
            for existing in deduped
        )
        if not dominated:
            deduped.append(card)
    assert len(deduped) == 2, "Cards with different fronts should both be kept"


# ---------------------------------------------------------------------------
# Test back-restates-front filter
# ---------------------------------------------------------------------------


def test_filter_back_restates_front():
    """Cards where back adds minimal new information over a short front are filtered."""
    cards = [
        {
            "front": "What is ATP?",
            "back": "ATP is the ATP.",
            "category": "terminology",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert result == [], f"Expected restatement card filtered, got: {result}"


def test_filter_back_restates_front_with_enough_new_words_kept():
    """Cards where back genuinely adds new information should be kept."""
    cards = [
        {
            "front": "What is ATP?",
            "back": (
                "ATP (adenosine triphosphate) is the primary energy currency of cells,"
                " providing energy through hydrolysis to ADP."
            ),
            "category": "terminology",
        },
    ]
    result = FlashcardGeneratorAgent._filter_low_quality(cards)
    assert len(result) == 1, "Card with substantive back should not be filtered"


# ---------------------------------------------------------------------------
# Test generate() accepts chapter_summary
# ---------------------------------------------------------------------------


def test_generate_accepts_chapter_summary():
    """Verify that chapter_summary text appears in the user prompt sent to the LLM."""
    captured_prompts = []

    mock_llm = MagicMock()
    mock_llm.chat.side_effect = lambda system, user, **kwargs: (
        captured_prompts.append(user) or
        json.dumps({"cards": [
            {
                "front": "Test question about enzymes?",
                "back": "Enzymes are biological catalysts that speed up chemical reactions.",
                "category": "key_facts",
            }
        ]})
    )

    agent = FlashcardGeneratorAgent(mock_llm)
    chunk = _make_chunk("Enzymes are proteins that catalyze biochemical reactions. " * 20)
    summary_text = "This chapter covers enzyme kinetics and catalytic mechanisms."

    agent.generate([chunk], chapter_summary=summary_text)

    assert len(captured_prompts) >= 1, "LLM should have been called at least once"
    first_prompt = captured_prompts[0]
    assert summary_text in first_prompt, (
        f"chapter_summary text should appear in user prompt.\nPrompt: {first_prompt[:300]}"
    )
