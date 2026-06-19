"""
Unit tests for DocumentOptimizerAgent and optimize_document_task.

Subject: application/agents/document_optimizer.py
         application/services/document_optimizer.py
Scope:   Agent optimize() — LLM call, context continuation, error handling.
         Task — happy path, chunked path, new document creation, truncation warning.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from api.tasks import Task
from application.agents.document_optimizer import DocumentOptimizerAgent
from application.services.document_optimizer import optimize_document_task
from core.ports.llm import GenerationParams

# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------


def _make_agent(
    reply: str = "## Overview\n\nOptimized doc.",
) -> tuple[DocumentOptimizerAgent, MagicMock]:
    mock_llm = MagicMock()
    mock_llm.chat.return_value = reply
    return DocumentOptimizerAgent(mock_llm), mock_llm


def test_optimize_returns_llm_output():
    """optimize() must return whatever the LLM produces."""
    agent, _ = _make_agent("## Overview\n\nOptimized.")
    result = agent.optimize("Some raw text.")
    assert result == "## Overview\n\nOptimized."


def test_optimize_passes_text_to_llm():
    """optimize() must pass the original text as the user message to the LLM."""
    agent, mock_llm = _make_agent()
    agent.optimize("Original document content.")
    _, user_msg = mock_llm.chat.call_args.args[:2]
    assert "Original document content." in user_msg


def test_optimize_passes_generation_params():
    """optimize() must forward GenerationParams to the LLM call."""
    agent, mock_llm = _make_agent()
    params = GenerationParams(temperature=0.3, top_p=0.9, max_tokens=4096)
    agent.optimize("Some text.", params=params)
    call_kwargs = mock_llm.chat.call_args.kwargs
    assert call_kwargs.get("params") is params


def test_optimize_with_none_params():
    """optimize() with params=None must still call the LLM without error."""
    agent, mock_llm = _make_agent()
    result = agent.optimize("Some text.", params=None)
    assert mock_llm.chat.called
    assert isinstance(result, str)


def test_optimize_propagates_llm_exception():
    """When the LLM raises, optimize() must re-raise the same exception."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = RuntimeError("LLM failure")
    agent = DocumentOptimizerAgent(mock_llm)

    with pytest.raises(RuntimeError, match="LLM failure"):
        agent.optimize("Some text.")


def test_optimize_uses_optimize_prompt():
    """optimize() must use the OPTIMIZE_DOCUMENT_SYSTEM prompt."""
    agent, mock_llm = _make_agent()
    agent.optimize("Some text.")
    system_msg = mock_llm.chat.call_args.args[0]
    assert "study guide" in system_msg
    assert "## Overview" in system_msg
    assert "## Suggested Questions" in system_msg


def test_optimize_with_agent_prompt():
    """optimize() must prepend agent_prompt to the system prompt."""
    agent, mock_llm = _make_agent()
    agent.optimize("Some text.", agent_prompt="Custom instructions.")
    system_msg = mock_llm.chat.call_args.args[0]
    assert system_msg.startswith("Custom instructions.")
    assert "study guide" in system_msg


def test_optimize_preserves_multiline_output():
    """optimize() returns the full multi-line LLM output without truncation."""
    expected = "## Overview\n\nSummary here.\n\n## Key Points\n\n- Item 1\n- Item 2"
    agent, _ = _make_agent(expected)
    assert agent.optimize("Raw text.") == expected


def test_optimize_preprocesses_input():
    """optimize() must detect and mark titles before sending to LLM."""
    agent, mock_llm = _make_agent("## Result")
    text = "Chapter Title\n\nSome body text.\n\nMore text."
    agent.optimize(text)
    _, user_msg = mock_llm.chat.call_args.args[:2]
    # Title should be marked with STRUCTURAL MARKERS
    assert "__HEADING__Chapter Title__END_HEADING__" in user_msg


def test_optimize_with_context():
    """optimize() with context must prepend a CONTINUATION INSTRUCTION."""
    agent, mock_llm = _make_agent("## Key Points\n\nContinued content.")
    agent.optimize("More text.", context="Previous section content")
    system_msg = mock_llm.chat.call_args.args[0]
    assert "CONTINUATION INSTRUCTION" in system_msg
    assert "previous section" in system_msg.lower()
    assert "Previous section content" in system_msg
    assert "Suggested Questions" in system_msg  # continuation says do NOT include
    assert "do NOT include" in system_msg


def test_optimize_retries_on_empty_response():
    """optimize() must retry on empty response errors."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = [
        ValueError("empty response"),
        ValueError("empty response"),
        "## Overview\n\nSuccess.",
    ]
    agent = DocumentOptimizerAgent(mock_llm)
    result = agent.optimize("Some text.")
    assert result == "## Overview\n\nSuccess."
    assert mock_llm.chat.call_count == 3


def test_optimize_raises_after_max_retries():
    """optimize() must raise after exhausting retries."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = ValueError("empty response")
    agent = DocumentOptimizerAgent(mock_llm)

    with pytest.raises(ValueError, match="empty response"):
        agent.optimize("Some text.")


# ---------------------------------------------------------------------------
# Background task tests
# ---------------------------------------------------------------------------


def _make_task() -> Task:
    return Task(task_id=str(uuid4()), task_type="kt_improve")


def _make_doc(**overrides):
    defaults = dict(
        id=uuid4(),
        tree_id=uuid4(),
        chapter_id=uuid4(),
        chapter_number=1,
        title="Test Chapter",
        content="Original chapter content for optimization.",
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
        file_type="md",
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_services(doc=None, **extra_services):
    doc = doc or _make_doc()
    services = MagicMock(**extra_services)
    services.kt_doc_store.get_document.return_value = doc

    # Mock create_document to return a new doc
    new_doc_id = uuid4()
    new_doc = _make_doc(
        id=new_doc_id,
        title=f"{doc.title} (Optimized)",
        content="## Overview\n\nOptimized content.",
        is_main=False,
        file_type="md",
    )
    services.kt_doc_store.create_document.return_value = new_doc
    services.kt_content_store.save_chunks.return_value = None

    # Provide real config values for chunking
    services.config.chunking.optimize_max_tokens = 6000
    services.config.chunking.optimize_overlap_tokens = 512
    return services


def test_optimize_document_task_returns_dict():
    """optimize_document_task must return a dict with document fields."""
    task = _make_task()
    doc = _make_doc(content="Short content for single-pass optimization.")
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.document_optimizer.DocumentOptimizerAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.optimize.return_value = "## Overview\n\nOptimized content."
            mock_agent_cls.return_value = mock_agent

            result = optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    assert isinstance(result, dict)
    assert result["content"] == "## Overview\n\nOptimized content."
    assert result["source_type"] == "optimized"
    assert "(Optimized)" in result["title"]


def test_optimize_document_task_creates_new_document():
    """optimize_document_task must create a NEW document in the same chapter."""
    task = _make_task()
    doc = _make_doc(content="Short content.")
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.document_optimizer.DocumentOptimizerAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.optimize.return_value = "## Overview\n\nOptimized."
            mock_agent_cls.return_value = mock_agent

            optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    services.kt_doc_store.create_document.assert_called_once()
    call_kwargs = services.kt_doc_store.create_document.call_args.kwargs
    assert call_kwargs["tree_id"] == tree_id
    assert call_kwargs["chapter_id"] == doc.chapter_id
    assert call_kwargs["is_main"] is False


def test_optimize_document_task_saves_chunks():
    """optimize_document_task must save chunks of the optimized output."""
    task = _make_task()
    doc = _make_doc(content="Short content.")
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.document_optimizer.DocumentOptimizerAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.optimize.return_value = "## Overview\n\nOptimized."
            mock_agent_cls.return_value = mock_agent

            optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    services.kt_content_store.save_chunks.assert_called_once()


def test_optimize_document_task_raises_on_empty_content():
    """optimize_document_task must raise if document has no content."""
    task = _make_task()
    doc = _make_doc(content="")
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent"):
        with pytest.raises(ValueError, match="no content"):
            optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )


def test_optimize_document_task_raises_on_missing_doc():
    """optimize_document_task must raise if document is not found."""
    task = _make_task()
    services = _make_services(None)  # get_document returns None
    services.kt_doc_store.get_document.return_value = None

    with patch("application.services.document_optimizer.resolve_llm_for_agent"):
        with pytest.raises(ValueError, match="not found"):
            optimize_document_task(
                task, uuid4(), uuid4(), services, uuid4(),
            )


def test_optimize_document_task_logs_truncation_warning(caplog):
    """optimize_document_task must warn if output is <20% of input length."""
    import logging
    caplog.set_level(logging.WARNING)

    task = _make_task()
    doc = _make_doc(content="Long content. " * 100)  # ~1500 chars
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.document_optimizer.DocumentOptimizerAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            # Return very short output to trigger truncation warning
            mock_agent.optimize.return_value = "Short."
            mock_agent_cls.return_value = mock_agent

            optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    assert "truncated" in caplog.text


# ---------------------------------------------------------------------------
# Chunked path tests
# ---------------------------------------------------------------------------


def test_optimize_document_task_chunked_path():
    """optimize_document_task must use chunked processing for large documents."""
    task = _make_task()
    # Create a large document with paragraph breaks to trigger chunking
    # Each paragraph is ~200 words; with 80 paragraphs = ~16000 words > 6000 threshold
    paragraph = "Word content. " * 100  # ~200 words per paragraph
    content = "\n\n".join([paragraph] * 80)  # 80 paragraphs
    doc = _make_doc(content=content)
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.document_optimizer.DocumentOptimizerAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.optimize.return_value = "## Overview\n\nChunk result."
            mock_agent_cls.return_value = mock_agent

            optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    # The agent should be called multiple times (chunked path)
    assert mock_agent.optimize.call_count > 1


def test_optimize_document_task_per_chunk_max_tokens():
    """Each chunk must use 1.5x multiplier with 4096 cap for max_tokens."""
    task = _make_task()
    # Multi-paragraph large document to trigger chunking
    paragraph = "Word content. " * 100  # ~200 words per paragraph
    content = "\n\n".join([paragraph] * 80)  # 80 paragraphs
    doc = _make_doc(content=content)
    tree_id = doc.tree_id
    services = _make_services(doc)

    with patch("application.services.document_optimizer.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)
        with patch("application.services.document_optimizer.DocumentOptimizerAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.optimize.return_value = "## Overview\n\nChunk result."
            mock_agent_cls.return_value = mock_agent

            optimize_document_task(
                task, doc.id, tree_id, services, uuid4(),
            )

    # Check that each chunk call had reasonable max_tokens
    for call_args in mock_agent.optimize.call_args_list:
        params = call_args.kwargs.get("params")
        if params and params.max_tokens:
            assert params.max_tokens >= 512  # floor
            assert params.max_tokens <= 4096  # cap
