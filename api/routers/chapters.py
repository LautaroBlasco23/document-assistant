"""Chapter analysis endpoints."""

import logging
import time

from fastapi import APIRouter

from api.deps import ServicesDep
from api.schemas.chapters import ChapterRequest, TaskResponseOut
from api.tasks import Task
from application.agents.question_generator import QuestionGeneratorAgent
from application.agents.summarizer import SummarizerAgent
from core.model.document import Chapter
from core.model.generated_content import Flashcard, QAPair, Summary

logger = logging.getLogger(__name__)

router = APIRouter()


def _set_progress(task: Task, pct: int, message: str) -> None:
    """Set both numeric and text progress on a task."""
    task.progress_pct = max(0, min(100, pct))
    task.progress = message
    logger.debug("Progress [%d%%]: %s", task.progress_pct, message)


def _summarize_background(
    task: Task, chapter_num: int, services: ServicesDep, document_hash: str, force: bool
) -> str:
    """Background task to summarize a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting summarize for chapter %d", chapter_num)
    try:
        chapter_index = chapter_num - 1

        # Return cached result if available and not forced
        if not force:
            cached = services.content_store.get_summary(document_hash, chapter_index)
            if cached:
                _set_progress(task, 100, "Loaded from cache")
                task.result = {"chapter": chapter_num, "summary": cached.content, "cached": True}
                logger.info("Returning cached summary for chapter %d", chapter_num)
                return cached.content

        _set_progress(task, 10, f"Retrieving context for chapter {chapter_num}...")
        chunks = services.retriever.retrieve(
            f"chapter {chapter_num} summary", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        logger.info(
            "Retrieved %d chunks for chapter %d (doc=%s)",
            len(chunks),
            chapter_num,
            document_hash[:12],
        )
        _set_progress(task, 25, f"Retrieved {len(chunks)} chunks, generating summary...")
        chapter_obj = Chapter(index=chapter_index, title=f"Chapter {chapter_num}", pages=[])

        def sum_progress(phase: str) -> None:
            if phase == "calling_llm":
                _set_progress(task, 40, "LLM is generating summary...")

        summary = SummarizerAgent(services.fast_llm).summarize(
            chapter_obj, chunks, on_progress=sum_progress
        )

        _set_progress(task, 85, "Saving summary...")
        services.content_store.save_summary(
            Summary(document_hash=document_hash, chapter_index=chapter_index, content=summary)
        )
        logger.debug("Persisted summary for doc=%s chapter=%d", document_hash[:12], chapter_index)

        _set_progress(task, 95, "Finalizing...")
        task.result = {"chapter": chapter_num, "summary": summary, "cached": False}
        elapsed = time.perf_counter() - t0
        logger.info("Completed summarize for chapter %d in %.1fs", chapter_num, elapsed)
        return summary
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise


def _generate_qa_background(
    task: Task, chapter_num: int, services: ServicesDep, document_hash: str, force: bool
) -> list[dict]:
    """Background task to generate Q&A for a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting questions for chapter %d", chapter_num)
    try:
        chapter_index = chapter_num - 1

        # Return cached result if available and not forced
        if not force:
            cached = services.content_store.get_qa_pairs(document_hash, chapter_index)
            if cached:
                qas = [{"question": p.question, "answer": p.answer} for p in cached]
                _set_progress(task, 100, "Loaded from cache")
                task.result = {"chapter": chapter_num, "qa_pairs": qas, "cached": True}
                logger.info("Returning cached Q&A for chapter %d", chapter_num)
                return qas

        _set_progress(task, 5, f"Retrieving context for chapter {chapter_num}...")
        chunks = services.retriever.retrieve(
            f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        logger.info(
            "Retrieved %d chunks for chapter %d (doc=%s)",
            len(chunks),
            chapter_num,
            document_hash[:12],
        )
        _set_progress(task, 20, f"Retrieved {len(chunks)} chunks, generating Q&A...")

        def qa_progress(batch: int, total: int, pairs_so_far: int) -> None:
            pct = 20 + int((batch / total) * 60)  # scale batches to 20%-80% range
            _set_progress(
                task, pct, f"Analyzing batch {batch}/{total} ({pairs_so_far} pairs generated)"
            )

        qas = QuestionGeneratorAgent(services.fast_llm).generate(chunks, on_progress=qa_progress)

        _set_progress(task, 85, f"Saving {len(qas)} Q&A pairs...")
        pairs = [
            QAPair(
                document_hash=document_hash,
                chapter_index=chapter_index,
                question=p["question"],
                answer=p["answer"],
            )
            for p in qas
        ]
        services.content_store.save_qa_pairs(pairs)
        logger.debug(
            "Persisted %d Q&A pairs for doc=%s chapter=%d",
            len(pairs),
            document_hash[:12],
            chapter_index,
        )

        _set_progress(task, 95, "Finalizing...")
        task.result = {"chapter": chapter_num, "qa_pairs": qas, "cached": False}
        elapsed = time.perf_counter() - t0
        logger.info("Completed questions for chapter %d in %.1fs", chapter_num, elapsed)
        return qas
    except Exception as e:
        logger.error(f"Q&A generation failed: {e}")
        raise


def _generate_flashcards_background(
    task: Task, chapter_num: int, services: ServicesDep, document_hash: str, force: bool
) -> list[dict]:
    """Background task to generate flashcards for a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting flashcards for chapter %d", chapter_num)
    try:
        chapter_index = chapter_num - 1

        # Return cached result if available and not forced
        if not force:
            cached = services.content_store.get_flashcards(document_hash, chapter_index)
            if cached:
                flashcards = [{"question": c.front, "answer": c.back} for c in cached]
                _set_progress(task, 100, "Loaded from cache")
                task.result = {"chapter": chapter_num, "flashcards": flashcards, "cached": True}
                logger.info("Returning cached flashcards for chapter %d", chapter_num)
                return flashcards

        _set_progress(task, 5, f"Retrieving context for chapter {chapter_num}...")
        chunks = services.retriever.retrieve(
            f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        logger.info(
            "Retrieved %d chunks for chapter %d (doc=%s)",
            len(chunks),
            chapter_num,
            document_hash[:12],
        )
        _set_progress(task, 20, f"Retrieved {len(chunks)} chunks, generating flashcards...")

        def fc_progress(batch: int, total: int, cards_so_far: int) -> None:
            pct = 20 + int((batch / total) * 60)
            _set_progress(
                task, pct, f"Building flashcards... batch {batch}/{total} ({cards_so_far} cards)"
            )

        # Flashcards are similar to Q&A, so reuse the generator
        qas = QuestionGeneratorAgent(services.fast_llm).generate(chunks, on_progress=fc_progress)

        _set_progress(task, 85, "Saving flashcards...")
        # Map question->front, answer->back for flashcard semantics
        cards = [
            Flashcard(
                document_hash=document_hash,
                chapter_index=chapter_index,
                front=p["question"],
                back=p["answer"],
            )
            for p in qas
        ]
        services.content_store.save_flashcards(cards)
        logger.debug(
            "Persisted %d flashcards for doc=%s chapter=%d",
            len(cards),
            document_hash[:12],
            chapter_index,
        )

        _set_progress(task, 95, "Finalizing...")
        task.result = {"chapter": chapter_num, "flashcards": qas, "cached": False}
        elapsed = time.perf_counter() - t0
        logger.info("Completed flashcards for chapter %d in %.1fs", chapter_num, elapsed)
        return qas
    except Exception as e:
        logger.error(f"Flashcard generation failed: {e}")
        raise


@router.post("/chapters/summarize", response_model=TaskResponseOut)
async def summarize_chapter(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to summarize a chapter."""
    task_id = services.task_registry.submit(
        _summarize_background, req.chapter, services, req.document_hash, req.force
    )
    logger.info("Chapter summarize task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="summarize")


@router.post("/chapters/questions", response_model=TaskResponseOut)
async def generate_qa(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to generate Q&A for a chapter."""
    task_id = services.task_registry.submit(
        _generate_qa_background, req.chapter, services, req.document_hash, req.force
    )
    logger.info("Chapter questions task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="questions")


@router.post("/chapters/flashcards", response_model=TaskResponseOut)
async def generate_flashcards(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to generate flashcards for a chapter."""
    task_id = services.task_registry.submit(
        _generate_flashcards_background, req.chapter, services, req.document_hash, req.force
    )
    logger.info("Chapter flashcards task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="flashcards")
