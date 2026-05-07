"""
Unit tests for TextImprovementAgent.

Subject: application/agents/text_improvement.py
Scope:   improve() — LLM call, error propagation.
"""

from unittest.mock import MagicMock

import pytest

from application.agents.text_improvement import TextImprovementAgent
from core.ports.llm import GenerationParams


def _make_agent(reply: str = "# Improved\n\nClean text.") -> tuple[TextImprovementAgent, MagicMock]:
    mock_llm = MagicMock()
    mock_llm.chat.return_value = reply
    return TextImprovementAgent(mock_llm), mock_llm


def test_improve_returns_llm_output():
    """improve() must return whatever the LLM produces."""
    agent, _ = _make_agent("# Better\n\nText here.")
    result = agent.improve("Some raw text.")
    assert result == "# Better\n\nText here."


def test_improve_passes_text_to_llm():
    """improve() must pass the original text as the user message to the LLM."""
    agent, mock_llm = _make_agent()
    agent.improve("Original document content.")
    _, user_msg = mock_llm.chat.call_args.args[:2]
    assert "Original document content." in user_msg


def test_improve_uses_system_prompt():
    """improve() must pass a system prompt that includes clarity/Markdown instructions."""
    agent, mock_llm = _make_agent()
    agent.improve("Some text.")
    system_msg = mock_llm.chat.call_args.args[0]
    assert "Markdown" in system_msg or "markdown" in system_msg.lower()
    assert "clarity" in system_msg.lower() or "clarity" in system_msg


def test_improve_passes_generation_params():
    """improve() must forward GenerationParams to the LLM call."""
    agent, mock_llm = _make_agent()
    params = GenerationParams(temperature=0.3, top_p=0.9, max_tokens=2048)
    agent.improve("Some text.", params=params)
    call_kwargs = mock_llm.chat.call_args.kwargs
    assert call_kwargs.get("params") is params


def test_improve_with_none_params():
    """improve() with params=None must still call the LLM without error."""
    agent, mock_llm = _make_agent()
    result = agent.improve("Some text.", params=None)
    assert mock_llm.chat.called
    assert isinstance(result, str)


def test_improve_propagates_llm_exception():
    """When the LLM raises, improve() must re-raise the same exception."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = RuntimeError("LLM failure")
    agent = TextImprovementAgent(mock_llm)

    with pytest.raises(RuntimeError, match="LLM failure"):
        agent.improve("Some text.")


def test_improve_preserves_multiline_output():
    """improve() returns the full multi-line LLM output without truncation."""
    expected = "## Heading\n\n- Item 1\n- Item 2\n\n**Bold text.**"
    agent, _ = _make_agent(expected)
    assert agent.improve("Raw text.") == expected
