"""Flashcard generation orchestration."""

import logging
import time
from uuid import UUID

from api.services import Services
from api.tasks import Task, set_task_progress
from application.agents.flashcard_generator import FlashcardGeneratorAgent
from application.llm_resolver import resolve_llm_for_agent
from core.model.chunk import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)


def generate_flashcard_task(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    _chapter_number: int,
    selected_text: str,
    services: Services,
) -> dict:
    """Background task: generate single flashcard from selected text."""
    try:
        set_task_progress(task, 10, "Generating flashcard...")
        agent = FlashcardGeneratorAgent(services.llm)
        flashcard = agent.create_flashcard(
            selected_text=selected_text,
            tree_id=str(tree_id),
            chapter_id=str(chapter_id),
        )
        set_task_progress(task, 70, "Saving flashcard...")
        services.kt_flashcard_store.save_flashcard(flashcard)
        set_task_progress(task, 100, "Done")
        return {"flashcard_id": str(flashcard.id)}
    except Exception as e:
        logger.error("Flashcard generation failed: %s", e)
        raise


def generate_flashcards_bulk_task(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    services: Services,
    user_id: UUID,
    num_flashcards: int | None = None,
    model: str | None = None,
    agent_id: str | None = None,
) -> dict:
    """Background task: generate batch flashcards from chapter chunks."""
    t0 = time.perf_counter()
    try:
        set_task_progress(task, 5, f"Retrieving chunks for chapter {chapter_number}...")
        kt_chunks = services.kt_content_store.get_chunks(tree_id, chapter_number)
        if not kt_chunks:
            raise ValueError(f"No content found for chapter {chapter_number}")

        chunks = [
            Chunk(
                text=kc.text,
                token_count=kc.token_count,
                metadata=ChunkMetadata(
                    source_file=str(kc.tree_id),
                    chapter_index=chapter_number - 1,
                    page_number=0,
                    start_char=0,
                    end_char=0,
                ),
            )
            for kc in kt_chunks
        ]

        set_task_progress(task, 15, "Starting flashcard generation...")
        agent_uid = UUID(agent_id) if agent_id else None
        llm, agent_prompt, _ = resolve_llm_for_agent(
            user_id, agent_uid, services, model_override=model
        )
        agent = FlashcardGeneratorAgent(llm)

        def on_progress(batch_i: int, total_batches: int) -> None:
            pct = 15 + int((batch_i / total_batches) * 75) if total_batches > 0 else 90
            set_task_progress(
                task, pct, f"Generating flashcards... batch {batch_i}/{total_batches}"
            )

        flashcards = agent.generate_batch(
            chunks,
            tree_id=tree_id,
            chapter_id=chapter_id,
            num_flashcards=num_flashcards,
            agent_prompt=agent_prompt or None,
            on_progress=on_progress,
        )

        set_task_progress(task, 90, f"Saving {len(flashcards)} flashcards...")
        for card in flashcards:
            services.kt_flashcard_store.save_flashcard(card)

        set_task_progress(task, 100, "Done")
        elapsed = time.perf_counter() - t0
        logger.info(
            "Generated %d flashcards for chapter %d in %.1fs",
            len(flashcards), chapter_number, elapsed,
        )
        return {"count": len(flashcards)}
    except Exception as e:
        logger.error("Bulk flashcard generation failed: %s", e)
        raise
