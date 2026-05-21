"""
Unit tests for question generation orchestration.

Subject: application/services/question_generation.py — generate_questions_task()
Scope:   Background task that generates questions for a knowledge chapter,
         including chunk retrieval, LLM resolution, per-type progress, and persistence.
Out of scope:
  - QuestionGeneratorAgent internals   → test_question_generator_agent.py
  - LLM provider behavior              → respective LLM provider tests
  - TaskRegistry lifecycle             → test_task_registry.py
Setup:   Mocked Services, Task, LLM resolver, and agent.
"""

from unittest.mock import MagicMock, patch, call
from uuid import UUID, uuid4

import pytest

from application.services.question_generation import generate_questions_task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task():
    """Return a mocked Task object."""
    return MagicMock()


def _make_services(chunks=None):
    """Return a mocked Services object."""
    services = MagicMock()
    services.kt_content_store.get_chunks.return_value = chunks or []
    return services


def _make_chunk(text="test content"):
    """Return a mocked knowledge tree chunk."""
    chunk = MagicMock()
    chunk.text = text
    chunk.token_count = 10
    chunk.tree_id = uuid4()
    return chunk


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_generate_questions_task_returns_counts():
    """On success, the task must return a dict with chapter number and type counts."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    mock_questions = {
        "true_false": [{"question": "Q1", "answer": "True"}],
        "multiple_choice": [{"question": "Q2", "options": ["A", "B"], "answer": "A"}],
    }

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            # Return different results for each question type (4 types by default)
            mock_agent.generate.side_effect = [
                {"true_false": mock_questions["true_false"]},
                {"multiple_choice": mock_questions["multiple_choice"]},
                {"matching": []},
                {"checkbox": []},
            ]
            mock_agent_cls.return_value = mock_agent

            result = generate_questions_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
            )

            assert result["chapter"] == 1
            assert result["counts"]["true_false"] == 1
            assert result["counts"]["multiple_choice"] == 1


def test_generate_questions_task_saves_questions():
    """Generated questions must be persisted via kt_question_store.save_questions()."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.return_value = {
                "true_false": [{"question": "Q1", "answer": "True"}]
            }
            mock_agent_cls.return_value = mock_agent

            generate_questions_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
            )

            services.kt_question_store.save_questions.assert_called_once()
            saved_questions = services.kt_question_store.save_questions.call_args[0][0]
            assert len(saved_questions) == 1
            assert saved_questions[0].tree_id == tree_id
            assert saved_questions[0].chapter_id == chapter_id
            assert saved_questions[0].question_type == "true_false"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_generate_questions_task_raises_when_no_chunks():
    """When no chunks exist for the chapter, the task must raise ValueError."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    services = _make_services(chunks=[])

    with pytest.raises(ValueError, match="No content found for chapter 1"):
        generate_questions_task(
            task, tree_id, chapter_id, chapter_number=1,
            services=services, user_id=user_id,
        )


def test_generate_questions_task_propagates_agent_error():
    """Agent errors must be propagated (not swallowed)."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.side_effect = RuntimeError("LLM failed")
            mock_agent_cls.return_value = mock_agent

            with pytest.raises(RuntimeError, match="LLM failed"):
                generate_questions_task(
                    task, tree_id, chapter_id, chapter_number=1,
                    services=services, user_id=user_id,
                )


# ---------------------------------------------------------------------------
# Progress updates
# ---------------------------------------------------------------------------


def test_generate_questions_task_updates_progress():
    """The task must update progress at key stages."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.return_value = {"true_false": []}
            mock_agent_cls.return_value = mock_agent

            generate_questions_task(
                task, tree_id, chapter_id, chapter_number=3,
                services=services, user_id=user_id,
            )

            # Check that set_task_progress was called
            from api.tasks import set_task_progress
            # Progress updates are done via the task mock
            assert task.progress_pct == 100
            assert task.progress == "Done"


# ---------------------------------------------------------------------------
# Custom question types
# ---------------------------------------------------------------------------


def test_generate_questions_task_respects_requested_types():
    """When requested_types is provided, only those types should be generated."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.return_value = {"checkbox": [{"question": "Q1"}]}
            mock_agent_cls.return_value = mock_agent

            result = generate_questions_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
                requested_types=["checkbox"],
            )

            # Only checkbox should be in counts
            assert "checkbox" in result["counts"]
            assert len(result["counts"]) == 1
            # Agent.generate should have been called once with question_types=["checkbox"]
            mock_agent.generate.assert_called_once()
            call_kwargs = mock_agent.generate.call_args[1]
            assert call_kwargs["question_types"] == ["checkbox"]


# ---------------------------------------------------------------------------
# Agent and model override
# ---------------------------------------------------------------------------


def test_generate_questions_task_passes_model_override():
    """When model is provided, it must be passed to resolve_llm_for_agent."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.return_value = {"true_false": []}
            mock_agent_cls.return_value = mock_agent

            generate_questions_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
                model="custom-model",
            )

            mock_resolve.assert_called_once()
            call_kwargs = mock_resolve.call_args[1]
            assert call_kwargs["model_override"] == "custom-model"


def test_generate_questions_task_passes_agent_id():
    """When agent_id is provided, it must be resolved to a UUID and passed to resolve_llm_for_agent."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])
    agent_id = str(uuid4())

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.return_value = {"true_false": []}
            mock_agent_cls.return_value = mock_agent

            generate_questions_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
                agent_id=agent_id,
            )

            mock_resolve.assert_called_once()
            call_args = mock_resolve.call_args[0]
            assert call_args[1] == UUID(agent_id)


def test_generate_questions_task_no_questions_generated():
    """When the agent returns no questions, save_questions must not be called."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.question_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.question_generation.QuestionGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate.return_value = {"true_false": []}
            mock_agent_cls.return_value = mock_agent

            generate_questions_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
            )

            services.kt_question_store.save_questions.assert_not_called()
