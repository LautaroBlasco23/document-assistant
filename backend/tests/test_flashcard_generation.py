"""
Unit tests for flashcard generation orchestration.

Subject: application/services/flashcard_generation.py — generate_flashcard_task(), generate_flashcards_bulk_task()
Scope:   Single flashcard generation and bulk flashcard generation background tasks.
Out of scope:
  - FlashcardGeneratorAgent internals  → test_flashcard_generator_agent.py
  - LLM provider behavior              → respective LLM provider tests
  - TaskRegistry lifecycle             → test_task_registry.py
Setup:   Mocked Services, Task, LLM resolver, and agent.
"""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from application.services.flashcard_generation import (
    generate_flashcard_task,
    generate_flashcards_bulk_task,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task():
    """Return a mocked Task object."""
    return MagicMock()


def _make_services(chunks=None, llm=None):
    """Return a mocked Services object."""
    services = MagicMock()
    services.kt_content_store.get_chunks.return_value = chunks or []
    services.llm = llm or MagicMock()
    return services


def _make_chunk(text="test content"):
    """Return a mocked knowledge tree chunk."""
    chunk = MagicMock()
    chunk.text = text
    chunk.token_count = 10
    chunk.tree_id = uuid4()
    return chunk


def _make_flashcard():
    """Return a mocked Flashcard object."""
    card = MagicMock()
    card.id = uuid4()
    return card


# ---------------------------------------------------------------------------
# generate_flashcard_task (single)
# ---------------------------------------------------------------------------


def test_generate_flashcard_task_returns_flashcard_id():
    """On success, the task must return a dict with the flashcard_id."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()
    flashcard = _make_flashcard()

    with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.create_flashcard.return_value = flashcard
        mock_agent_cls.return_value = mock_agent

        result = generate_flashcard_task(
            task, tree_id, chapter_id, 1,
            selected_text="Some selected text",
            services=services,
        )

        assert result["flashcard_id"] == str(flashcard.id)


def test_generate_flashcard_task_saves_flashcard():
    """The generated flashcard must be persisted via kt_flashcard_store."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()
    flashcard = _make_flashcard()

    with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.create_flashcard.return_value = flashcard
        mock_agent_cls.return_value = mock_agent

        generate_flashcard_task(
            task, tree_id, chapter_id, 1,
            selected_text="Some selected text",
            services=services,
        )

        services.kt_flashcard_store.save_flashcard.assert_called_once_with(flashcard)


def test_generate_flashcard_task_passes_correct_args():
    """create_flashcard must be called with selected_text, tree_id, and chapter_id."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()
    flashcard = _make_flashcard()

    with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.create_flashcard.return_value = flashcard
        mock_agent_cls.return_value = mock_agent

        generate_flashcard_task(
            task, tree_id, chapter_id, 1,
            selected_text="Important concept",
            services=services,
        )

        mock_agent.create_flashcard.assert_called_once()
        call_kwargs = mock_agent.create_flashcard.call_args[1]
        assert call_kwargs["selected_text"] == "Important concept"
        assert call_kwargs["tree_id"] == str(tree_id)
        assert call_kwargs["chapter_id"] == str(chapter_id)


def test_generate_flashcard_task_propagates_error():
    """Agent errors must be propagated."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()

    with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.create_flashcard.side_effect = ValueError("Invalid text")
        mock_agent_cls.return_value = mock_agent

        with pytest.raises(ValueError, match="Invalid text"):
            generate_flashcard_task(
                task, tree_id, chapter_id, 1,
                selected_text="text",
                services=services,
            )


# ---------------------------------------------------------------------------
# generate_flashcards_bulk_task
# ---------------------------------------------------------------------------


def test_generate_flashcards_bulk_task_returns_count():
    """On success, the task must return a dict with the flashcard count."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])
    flashcards = [_make_flashcard(), _make_flashcard()]

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.return_value = flashcards
            mock_agent_cls.return_value = mock_agent

            result = generate_flashcards_bulk_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
            )

            assert result["count"] == 2


def test_generate_flashcards_bulk_task_raises_when_no_chunks():
    """When no chunks exist for the chapter, the task must raise ValueError."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    services = _make_services(chunks=[])

    with pytest.raises(ValueError, match="No content found for chapter 1"):
        generate_flashcards_bulk_task(
            task, tree_id, chapter_id, chapter_number=1,
            services=services, user_id=user_id,
        )


def test_generate_flashcards_bulk_task_saves_each_flashcard():
    """Each generated flashcard must be saved individually."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])
    flashcards = [_make_flashcard(), _make_flashcard(), _make_flashcard()]

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.return_value = flashcards
            mock_agent_cls.return_value = mock_agent

            generate_flashcards_bulk_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
            )

            assert services.kt_flashcard_store.save_flashcard.call_count == 3
            for card in flashcards:
                services.kt_flashcard_store.save_flashcard.assert_any_call(card)


def test_generate_flashcards_bulk_task_passes_num_flashcards():
    """num_flashcards must be passed to generate_batch."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.return_value = []
            mock_agent_cls.return_value = mock_agent

            generate_flashcards_bulk_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
                num_flashcards=10,
            )

            mock_agent.generate_batch.assert_called_once()
            call_kwargs = mock_agent.generate_batch.call_args[1]
            assert call_kwargs["num_flashcards"] == 10


def test_generate_flashcards_bulk_task_passes_model_override():
    """model must be passed to resolve_llm_for_agent as model_override."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.return_value = []
            mock_agent_cls.return_value = mock_agent

            generate_flashcards_bulk_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
                model="custom-model",
            )

            mock_resolve.assert_called_once()
            call_kwargs = mock_resolve.call_args[1]
            assert call_kwargs["model_override"] == "custom-model"


def test_generate_flashcards_bulk_task_passes_agent_id():
    """agent_id must be resolved to UUID and passed to resolve_llm_for_agent."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])
    agent_id = str(uuid4())

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.return_value = []
            mock_agent_cls.return_value = mock_agent

            generate_flashcards_bulk_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
                agent_id=agent_id,
            )

            mock_resolve.assert_called_once()
            call_args = mock_resolve.call_args[0]
            assert call_args[1] == UUID(agent_id)


def test_generate_flashcards_bulk_task_no_flashcards_generated():
    """When no flashcards are generated, save_flashcard must not be called."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.return_value = []
            mock_agent_cls.return_value = mock_agent

            generate_flashcards_bulk_task(
                task, tree_id, chapter_id, chapter_number=1,
                services=services, user_id=user_id,
            )

            services.kt_flashcard_store.save_flashcard.assert_not_called()


def test_generate_flashcards_bulk_task_propagates_error():
    """Agent errors must be propagated."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    user_id = uuid4()
    chunk = _make_chunk()
    services = _make_services(chunks=[chunk])

    with patch("application.services.flashcard_generation.resolve_llm_for_agent") as mock_resolve:
        mock_llm = MagicMock()
        mock_resolve.return_value = (mock_llm, None, None)

        with patch("application.services.flashcard_generation.FlashcardGeneratorAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.generate_batch.side_effect = RuntimeError("Generation failed")
            mock_agent_cls.return_value = mock_agent

            with pytest.raises(RuntimeError, match="Generation failed"):
                generate_flashcards_bulk_task(
                    task, tree_id, chapter_id, chapter_number=1,
                    services=services, user_id=user_id,
                )
