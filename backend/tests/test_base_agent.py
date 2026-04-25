"""
Subject: application/agents/base.py — BaseAgent and _strip_code_fences
Scope:   Prompt dispatch to LLM, JSON parsing with retry logic, markdown fence stripping
Out of scope:
  - concrete agent behaviors (chat, flashcards, questions) → sibling test files
  - real LLM network calls → mocked at the LLM port level
Setup:   LLM collaborator is a unittest.mock.MagicMock(spec=LLM).
"""

import json
from unittest.mock import MagicMock

import pytest

from application.agents.base import BaseAgent, _strip_code_fences
from core.ports.llm import LLM


# ---------------------------------------------------------------------------
# _strip_code_fences
# ---------------------------------------------------------------------------

# Strips leading/trailing markdown code fences when the LLM wraps JSON in ```json ... ```.
def test_strip_code_fences_json_tag():
    fenced = '```json\n{"key": "value"}\n```'
    result = _strip_code_fences(fenced)
    assert result == '{"key": "value"}'


# Strips generic triple-backtick fences when no language tag is present.
def test_strip_code_fences_no_tag():
    fenced = '```\nplain text\n```'
    result = _strip_code_fences(fenced)
    assert result == "plain text"


# Leaves plain text untouched when no fences are present.
def test_strip_code_fences_plain_text():
    plain = "just some text"
    result = _strip_code_fences(plain)
    assert result == "just some text"


# ---------------------------------------------------------------------------
# BaseAgent._call
# ---------------------------------------------------------------------------

# Passes the system prompt as the first argument and user prompt as the second to LLM.chat().
def test_call_passes_system_and_user():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "response"
    agent = BaseAgent(llm)

    result = agent._call("system prompt", "user prompt")

    assert result == "response"
    llm.chat.assert_called_once_with("system prompt", "user prompt", params=None)


# ---------------------------------------------------------------------------
# BaseAgent._call_json
# ---------------------------------------------------------------------------

# Calls LLM.chat with format="json" and returns the stripped response when it is valid JSON.
def test_call_json_returns_stripped_json():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '{"answer": 42}'
    agent = BaseAgent(llm)

    result = agent._call_json("system", "user")

    llm.chat.assert_called_once_with("system", "user", format="json", params=None)
    assert result == '{"answer": 42}'


# Strips markdown fences from the LLM response before returning it.
def test_call_json_strips_fences():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '```json\n{"ok": true}\n```'
    agent = BaseAgent(llm)

    result = agent._call_json("sys", "usr")

    assert result == '{"ok": true}'


# ---------------------------------------------------------------------------
# BaseAgent._call_json_with_retry
# ---------------------------------------------------------------------------

# Returns immediately when the first response is already valid JSON (no retry needed).
def test_call_json_with_retry_succeeds_first_try():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = '{"valid": true}'
    agent = BaseAgent(llm)

    result = agent._call_json_with_retry("sys", "usr", max_retries=1)

    assert json.loads(result) == {"valid": True}
    assert llm.chat.call_count == 1


# Retries once when the first response is malformed and max_retries allows it.
def test_call_json_with_retry_retries_on_malformed():
    llm = MagicMock(spec=LLM)
    llm.chat.side_effect = ["not json", '{"fixed": true}']
    agent = BaseAgent(llm)

    result = agent._call_json_with_retry("sys", "usr", max_retries=1)

    assert json.loads(result) == {"fixed": True}
    assert llm.chat.call_count == 2
    # second call appends a correction prompt to the user message
    second_user = llm.chat.call_args_list[1][0][1]
    assert "valid JSON" in second_user


# Does not retry when max_retries is 0; returns the raw malformed response.
def test_call_json_with_retry_no_retries_when_zero():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "still not json"
    agent = BaseAgent(llm)

    result = agent._call_json_with_retry("sys", "usr", max_retries=0)

    assert result == "still not json"
    assert llm.chat.call_count == 1


# Succeeds on the retry when the first attempt is fenced but otherwise malformed after stripping.
# Edge: the first attempt is not valid JSON even after fence stripping, so a retry is triggered.
def test_call_json_with_retry_malformed_after_strip():
    llm = MagicMock(spec=LLM)
    llm.chat.side_effect = ['```json\nbad\n```', '{"ok": 1}']
    agent = BaseAgent(llm)

    result = agent._call_json_with_retry("sys", "usr", max_retries=1)

    assert json.loads(result) == {"ok": 1}
    assert llm.chat.call_count == 2
