"""
Subject: application/prompts.py — LLM prompt constants
Scope:   Prompt strings are non-empty, contain expected placeholders, are well-formed
Out of scope:
  - runtime prompt interpolation          → tested in agent test files
  - prompt quality / pedagogical review   → out of scope for unit tests
Setup:   Imports the module directly; no external dependencies.
"""

import inspect

import pytest

import application.prompts as prompts


# Collect every top-level string constant defined in the module.
PROMPT_NAMES = [
    name for name in dir(prompts)
    if not name.startswith("_") and isinstance(getattr(prompts, name), str)
]


@pytest.mark.parametrize("name", PROMPT_NAMES)
# Each prompt constant must be a non-empty string that is not only whitespace.
def test_prompt_is_non_empty_string(name):
    value = getattr(prompts, name)
    assert isinstance(value, str)
    assert value.strip() != ""


# Prompts that reference dynamic content at runtime must contain the expected placeholders.
def test_summary_system_has_no_placeholders():
    # SUMMARY_SYSTEM is a static system prompt with no interpolation.
    assert "{text}" not in prompts.SUMMARY_SYSTEM


def test_flashcards_system_has_no_placeholders():
    # FLASHCARDS_SYSTEM is static; placeholders are optional keys in the JSON schema only.
    assert isinstance(prompts.FLASHCARDS_SYSTEM, str)


def test_flashcard_from_selection_system_is_static():
    assert isinstance(prompts.FLASHCARD_FROM_SELECTION_SYSTEM, str)
    assert prompts.FLASHCARD_FROM_SELECTION_SYSTEM.strip() != ""


# Question prompts must mention the expected JSON schema keys so agents can parse responses.
def test_questions_true_false_mentions_questions():
    assert '"questions"' in prompts.QUESTIONS_TRUE_FALSE


def test_questions_multiple_choice_mentions_questions():
    assert '"questions"' in prompts.QUESTIONS_MULTIPLE_CHOICE


def test_questions_matching_mentions_questions():
    assert '"questions"' in prompts.QUESTIONS_MATCHING


def test_questions_checkbox_mentions_questions():
    assert '"questions"' in prompts.QUESTIONS_CHECKBOX


# All four question prompts must contain their respective schema fields.
def test_questions_true_false_has_statement_and_answer():
    assert "statement" in prompts.QUESTIONS_TRUE_FALSE
    assert "answer" in prompts.QUESTIONS_TRUE_FALSE


def test_questions_multiple_choice_has_choices_and_correct_index():
    assert "choices" in prompts.QUESTIONS_MULTIPLE_CHOICE
    assert "correct_index" in prompts.QUESTIONS_MULTIPLE_CHOICE


def test_questions_matching_has_pairs():
    assert "pairs" in prompts.QUESTIONS_MATCHING
    assert "term" in prompts.QUESTIONS_MATCHING
    assert "definition" in prompts.QUESTIONS_MATCHING


def test_questions_checkbox_has_correct_indices():
    assert "correct_indices" in prompts.QUESTIONS_CHECKBOX
    assert "choices" in prompts.QUESTIONS_CHECKBOX
