"""
Subject: application/agents/question_generator.py — QuestionGeneratorAgent
Scope:   generate() for each question type, per-type validators rejecting bad data
Out of scope:
  - batching internals                     → test_batching.py
  - base-agent JSON/retry logic            → test_base_agent.py
Setup:   LLM collaborator is a unittest.mock.MagicMock(spec=LLM).
         Chunk fixtures are lightweight dataclasses.
"""

import json
from unittest.mock import MagicMock

import pytest

from application.agents.question_generator import QuestionGeneratorAgent
from core.model.chunk import Chunk, ChunkMetadata
from core.model.question import QuestionType
from core.ports.llm import LLM


def _chunk(text: str) -> Chunk:
    """Build a Chunk with the given text."""
    return Chunk(text=text, metadata=ChunkMetadata(
        source_file="test", chapter_index=0, page_number=1, start_char=0, end_char=len(text)
    ))


# ---------------------------------------------------------------------------
# generate() — true_false
# ---------------------------------------------------------------------------

# Returns validated true/false questions when the LLM emits a proper JSON array.
def test_generate_true_false():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = json.dumps({
        "questions": [
            {"statement": "The sky is blue.", "answer": True},
            {"statement": "The sky is green.", "answer": False},
        ]
    })
    agent = QuestionGeneratorAgent(llm)

    result = agent.generate([_chunk("sky info")], question_types=["true_false"])

    assert len(result["true_false"]) == 2
    assert result["true_false"][0]["answer"] is True


# ---------------------------------------------------------------------------
# generate() — multiple_choice
# ---------------------------------------------------------------------------

# Returns validated multiple-choice questions with exactly 4 choices and a valid correct_index.
def test_generate_multiple_choice():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = json.dumps({
        "questions": [
            {
                "question": "What is 2+2?",
                "choices": ["1", "2", "3", "4"],
                "correct_index": 3,
            }
        ]
    })
    agent = QuestionGeneratorAgent(llm)

    result = agent.generate([_chunk("math")], question_types=["multiple_choice"])

    assert len(result["multiple_choice"]) == 1
    assert result["multiple_choice"][0]["correct_index"] == 3


# ---------------------------------------------------------------------------
# generate() — matching
# ---------------------------------------------------------------------------

# Returns validated matching questions with unique term-definition pairs.
def test_generate_matching():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = json.dumps({
        "questions": [
            {
                "prompt": "Match terms",
                "pairs": [
                    {"term": "A", "definition": "Alpha"},
                    {"term": "B", "definition": "Beta"},
                    {"term": "C", "definition": "Gamma"},
                ]
            }
        ]
    })
    agent = QuestionGeneratorAgent(llm)

    result = agent.generate([_chunk("abc")], question_types=["matching"])

    assert len(result["matching"]) == 1
    assert len(result["matching"][0]["pairs"]) == 3


# ---------------------------------------------------------------------------
# generate() — checkbox
# ---------------------------------------------------------------------------

# Returns validated checkbox questions with correct_indices within bounds.
def test_generate_checkbox():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = json.dumps({
        "questions": [
            {
                "question": "Select primes",
                "choices": ["2", "3", "4", "5"],
                "correct_indices": [0, 1, 3],
            }
        ]
    })
    agent = QuestionGeneratorAgent(llm)

    result = agent.generate([_chunk("primes")], question_types=["checkbox"])

    assert len(result["checkbox"]) == 1
    assert result["checkbox"][0]["correct_indices"] == [0, 1, 3]


# ---------------------------------------------------------------------------
# generate() — bad JSON / missing fields
# ---------------------------------------------------------------------------

# Skips questions that fail validation due to missing required fields.
def test_generate_skips_invalid_items():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = json.dumps({
        "questions": [
            {"statement": "Missing answer key"},  # invalid: no answer
            {"statement": "Valid one.", "answer": True},  # valid
        ]
    })
    agent = QuestionGeneratorAgent(llm)

    result = agent.generate([_chunk("mixed")], question_types=["true_false"])

    assert len(result["true_false"]) == 1
    assert result["true_false"][0]["answer"] is True


# Returns empty lists for all requested types when chunks are empty.
def test_generate_empty_chunks():
    llm = MagicMock(spec=LLM)
    agent = QuestionGeneratorAgent(llm)

    result = agent.generate([], question_types=["true_false"])

    assert result == {"true_false": []}
    llm.chat.assert_not_called()


# ---------------------------------------------------------------------------
# _validate_true_false
# ---------------------------------------------------------------------------

# Rejects items missing the 'statement' field.
def test_validate_true_false_missing_statement():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_true_false({"answer": True}) is False


# Rejects items where the statement starts with 'True or false:'.
def test_validate_true_false_prefixed():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_true_false({"statement": "True or false: the sky is blue.", "answer": True}) is False


# Rejects items where the answer is not a boolean.
def test_validate_true_false_bad_type():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_true_false({"statement": "Sky is blue.", "answer": "yes"}) is False


# ---------------------------------------------------------------------------
# _validate_multiple_choice
# ---------------------------------------------------------------------------

# Rejects items with fewer than 4 choices.
def test_validate_multiple_choice_too_few_choices():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_multiple_choice({
        "question": "Q", "choices": ["a", "b", "c"], "correct_index": 0
    }) is False


# Rejects items with an out-of-bounds correct_index.
def test_validate_multiple_choice_bad_index():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_multiple_choice({
        "question": "Q", "choices": ["a", "b", "c", "d"], "correct_index": 4
    }) is False


# Rejects items containing an empty choice string.
def test_validate_multiple_choice_empty_choice():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_multiple_choice({
        "question": "Q", "choices": ["a", "", "c", "d"], "correct_index": 0
    }) is False


# ---------------------------------------------------------------------------
# _validate_matching
# ---------------------------------------------------------------------------

# Rejects items with fewer than 3 pairs.
def test_validate_matching_too_few_pairs():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_matching({"pairs": [{"term": "A", "definition": "B"}]}) is False


# Rejects items with duplicate terms.
def test_validate_matching_duplicate_terms():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_matching({
        "pairs": [
            {"term": "A", "definition": "B"},
            {"term": "A", "definition": "C"},
            {"term": "D", "definition": "E"},
        ]
    }) is False


# Rejects items with duplicate definitions.
def test_validate_matching_duplicate_definitions():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_matching({
        "pairs": [
            {"term": "A", "definition": "X"},
            {"term": "B", "definition": "X"},
            {"term": "C", "definition": "Y"},
        ]
    }) is False


# Rejects a pair containing an empty term.
def test_validate_matching_empty_term():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_matching({
        "pairs": [
            {"term": "", "definition": "B"},
            {"term": "A", "definition": "C"},
            {"term": "D", "definition": "E"},
        ]
    }) is False


# ---------------------------------------------------------------------------
# _validate_checkbox
# ---------------------------------------------------------------------------

# Rejects items where all choices are marked correct.
def test_validate_checkbox_all_correct():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_checkbox({
        "question": "Q",
        "choices": ["a", "b", "c", "d"],
        "correct_indices": [0, 1, 2, 3],
    }) is False


# Rejects items with fewer than 2 correct indices.
def test_validate_checkbox_too_few_correct():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_checkbox({
        "question": "Q",
        "choices": ["a", "b", "c", "d"],
        "correct_indices": [0],
    }) is False


# Rejects items with an out-of-bounds index.
def test_validate_checkbox_out_of_bounds():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_checkbox({
        "question": "Q",
        "choices": ["a", "b", "c", "d"],
        "correct_indices": [0, 4],
    }) is False


# Rejects items with duplicate indices.
def test_validate_checkbox_duplicate_indices():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_checkbox({
        "question": "Q",
        "choices": ["a", "b", "c", "d"],
        "correct_indices": [0, 0, 1],
    }) is False


# Rejects items with fewer than 4 choices.
def test_validate_checkbox_too_few_choices():
    agent = QuestionGeneratorAgent(MagicMock(spec=LLM))
    assert agent._validate_checkbox({
        "question": "Q",
        "choices": ["a", "b", "c"],
        "correct_indices": [0, 1],
    }) is False
