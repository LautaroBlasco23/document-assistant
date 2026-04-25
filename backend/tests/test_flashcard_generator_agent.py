"""
Subject: application/agents/flashcard_generator.py — FlashcardGeneratorAgent
Scope:   Generating flashcard dicts, creating Flashcard domain objects, fence stripping
Out of scope:
  - retry logic or base-agent internals  → test_base_agent.py
  - question generation                  → test_question_generator_agent.py
Setup:   LLM collaborator is a unittest.mock.MagicMock(spec=LLM).
"""

import json
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from application.agents.flashcard_generator import FlashcardGeneratorAgent
from core.model.knowledge_tree import Flashcard
from core.ports.llm import LLM


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------

# Returns a dict with 'front' and 'back' keys populated from the LLM JSON response.
def test_generate_returns_front_and_back():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '{"front": "What is Python?", "back": "A programming language."}'
    agent = FlashcardGeneratorAgent(llm)

    result = agent.generate("some text")

    assert result["front"] == "What is Python?"
    assert result["back"] == "A programming language."


# Strips markdown code fences from the LLM response before parsing JSON.
def test_generate_strips_code_fences():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '```json\n{"front": "Q", "back": "A"}\n```'
    agent = FlashcardGeneratorAgent(llm)

    result = agent.generate("text")

    assert result == {"front": "Q", "back": "A"}


# Raises JSONDecodeError when the LLM returns truly unparseable JSON (no retry in this agent).
def test_generate_malformed_json_raises():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "not json"
    agent = FlashcardGeneratorAgent(llm)

    with pytest.raises(json.JSONDecodeError):
        agent.generate("text")


# ---------------------------------------------------------------------------
# create_flashcard()
# ---------------------------------------------------------------------------

# Returns a Flashcard domain object with the correct fields sourced from generate().
def test_create_flashcard_returns_domain_object():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '{"front": "Capital of France?", "back": "Paris"}'
    agent = FlashcardGeneratorAgent(llm)

    fc = agent.create_flashcard("France is a country.", tree_id="tree-uuid", chapter_id="ch-uuid")

    assert isinstance(fc, Flashcard)
    assert isinstance(fc.id, UUID)
    assert fc.tree_id == "tree-uuid"
    assert fc.chapter_id == "ch-uuid"
    assert fc.front == "Capital of France?"
    assert fc.back == "Paris"
    assert fc.source_text == "France is a country."
    assert isinstance(fc.created_at, datetime)


# Uses the LLM response for front/back even when the selected text is empty.
def test_create_flashcard_empty_selected_text():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '{"front": "Q", "back": "A"}'
    agent = FlashcardGeneratorAgent(llm)

    fc = agent.create_flashcard("", tree_id="t", chapter_id="c")

    assert fc.source_text == ""
    assert fc.front == "Q"
