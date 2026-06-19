"""
Unit tests for TextImprovementAgent.

Subject: application/agents/text_improvement.py
Scope:   improve() — LLM call, error propagation.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from api.tasks import Task
from application.agents.text_improvement import TextImprovementAgent
from application.services.text_improvement import improve_document_task
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


def test_improve_uses_formatting_prompt():
    """improve() must use the formatting system prompt by default."""
    agent, mock_llm = _make_agent()
    agent.improve("Some text.")
    system_msg = mock_llm.chat.call_args.args[0]
    assert "Markdown formatting validator" in system_msg
    assert "__HEADING__" in system_msg or "STRUCTURAL MARKERS" in system_msg
    assert "DO NOT" in system_msg


def test_improve_formatting_with_agent_prompt():
    """improve() must prepend agent_prompt to the formatting prompt."""
    agent, mock_llm = _make_agent()
    agent.improve("Some text.", agent_prompt="Custom instructions.")
    system_msg = mock_llm.chat.call_args.args[0]
    assert system_msg.startswith("Custom instructions.")
    assert "Markdown formatting" in system_msg


def test_improve_preprocesses_input():
    """improve() must remove duplicates and mark titles before sending to LLM."""
    agent, mock_llm = _make_agent("## Result")
    # Input with a duplicate paragraph and a title
    text = "The Trunchbull\n\nSome body text.\n\nThe Trunchbull\n\nMore text."
    agent.improve(text)
    _, user_msg = mock_llm.chat.call_args.args[:2]
    # Title should be marked
    assert "__HEADING__The Trunchbull__END_HEADING__" in user_msg
    # Duplicate should be removed
    assert user_msg.count("The Trunchbull") == 1


def test_improve_formatting_preprocesses_input():
    """improve() must preprocess input for formatting."""
    agent, mock_llm = _make_agent("## Result")
    text = "Chapter One\n\nSome text.\n\nChapter One\n\nMore text."
    agent.improve(text)
    _, user_msg = mock_llm.chat.call_args.args[:2]
    assert "__HEADING__Chapter One__END_HEADING__" in user_msg
    assert user_msg.count("Chapter One") == 1


def test_improve_passes_preprocessed_text_not_raw():
    """The user message sent to the LLM must be the preprocessed version."""
    agent, mock_llm = _make_agent("Result")
    raw = "Title\n\nBody.\n\nTitle\n\nBody."
    agent.improve(raw)
    _, user_msg = mock_llm.chat.call_args.args[:2]
    # Should not contain duplicate paragraphs
    assert user_msg.count("Body.") == 1


# ---------------------------------------------------------------------------
# Background task tests
# ---------------------------------------------------------------------------


def _make_task() -> Task:
    return Task(task_id=str(uuid4()), task_type="kt_improve")


def _make_doc(**overrides):
    defaults = dict(
        id=uuid4(),
        tree_id=uuid4(),
        chapter_id=None,
        chapter_number=None,
        title="Test Doc",
        content="Original content.",
        original_content=None,
        is_main=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        source_file_path=None,
        source_file_name=None,
        page_start=None,
        page_end=None,
        source_type="file",
        source_url=None,
        file_type=None,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_services(doc=None):
    services = MagicMock()
    services.kt_doc_store.get_document.return_value = doc or _make_doc()
    updated = _make_doc(content="# Improved\n\nContent.", original_content="Original content.")
    services.kt_doc_store.save_improvement.return_value = updated
    # Provide real config values for chunking
    services.config.chunking.improve_max_tokens = 2000
    services.config.chunking.improve_overlap_tokens = 256
    return services


def test_improve_document_task_returns_document_dict():
    """improve_document_task must return a dict with document fields."""
    task = _make_task()
    doc = _make_doc()
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.text_improvement.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.text_improvement.TextImprovementAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.improve.return_value = "# Improved\n\nContent."
            mock_agent_cls.return_value = mock_agent

            result = improve_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    assert isinstance(result, dict)
    assert result["content"] == "# Improved\n\nContent."
    assert result["original_content"] == "Original content."
    assert result["title"] == "Test Doc"


def test_improve_document_task_uses_formatting_prompt():
    """improve_document_task must use the formatting system prompt."""
    task = _make_task()
    doc = _make_doc()
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.text_improvement.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.text_improvement.TextImprovementAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.improve.return_value = "# Formatted"
            mock_agent_cls.return_value = mock_agent

            improve_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    mock_agent.improve.assert_called_once()


def test_improve_document_task_saves_improvement():
    """improve_document_task must save the improvement to the store."""
    task = _make_task()
    doc = _make_doc()
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.text_improvement.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.text_improvement.TextImprovementAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.improve.return_value = "# Improved"
            mock_agent_cls.return_value = mock_agent

            improve_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    services.kt_doc_store.save_improvement.assert_called_once_with(doc.id, "# Improved")
