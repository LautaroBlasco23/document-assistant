"""Chapter analysis endpoints."""

import logging
import time

from fastapi import APIRouter, HTTPException

from api.deps import ServicesDep
from api.schemas.chapters import ChapterRequest, TaskResponseOut
from api.tasks import Task
from application.agents.question_generator import QuestionGeneratorAgent
from application.agents.summarizer import SummarizerAgent
from core.model.document import Chapter, Document

logger = logging.getLogger(__name__)

router = APIRouter()


def _summarize_background(task: Task, chapter_num: int, services: ServicesDep) -> str:
    """Background task to summarize a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting summarize for chapter %d", chapter_num)
    try:
        chapter_index = chapter_num - 1
        task.progress = f"Retrieving context for chapter {chapter_num}..."

        chunks = services.retriever.retrieve(
            f"chapter {chapter_num} summary", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        task.progress = "Generating summary..."
        chapter_obj = Chapter(index=chapter_index, title=f"Chapter {chapter_num}", pages=[])
        summary = SummarizerAgent(services.fast_llm).summarize(chapter_obj, chunks)

        task.result = {"chapter": chapter_num, "summary": summary}
        logger.info("Completed summarize for chapter %d in %.1fs", chapter_num, time.perf_counter() - t0)
        return summary
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise


def _generate_qa_background(task: Task, chapter_num: int, services: ServicesDep) -> list[dict]:
    """Background task to generate Q&A for a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting questions for chapter %d", chapter_num)
    try:
        chapter_index = chapter_num - 1
        task.progress = f"Retrieving context for chapter {chapter_num}..."

        chunks = services.retriever.retrieve(
            f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        task.progress = "Generating Q&A..."
        qas = QuestionGeneratorAgent(services.fast_llm).generate(chunks)

        task.result = {"chapter": chapter_num, "qa_pairs": qas}
        logger.info("Completed questions for chapter %d in %.1fs", chapter_num, time.perf_counter() - t0)
        return qas
    except Exception as e:
        logger.error(f"Q&A generation failed: {e}")
        raise


def _generate_flashcards_background(
    task: Task, chapter_num: int, services: ServicesDep
) -> list[dict]:
    """Background task to generate flashcards for a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting flashcards for chapter %d", chapter_num)
    try:
        chapter_index = chapter_num - 1
        task.progress = f"Retrieving context for chapter {chapter_num}..."

        chunks = services.retriever.retrieve(
            f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        task.progress = "Generating flashcards..."
        # Flashcards are similar to Q&A, so reuse the generator
        qas = QuestionGeneratorAgent(services.fast_llm).generate(chunks)

        task.result = {"chapter": chapter_num, "flashcards": qas}
        logger.info("Completed flashcards for chapter %d in %.1fs", chapter_num, time.perf_counter() - t0)
        return qas
    except Exception as e:
        logger.error(f"Flashcard generation failed: {e}")
        raise


@router.post("/chapters/summarize", response_model=TaskResponseOut)
async def summarize_chapter(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to summarize a chapter."""
    task_id = services.task_registry.submit(
        _summarize_background, req.chapter, services
    )
    logger.info("Chapter summarize task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="summarize")


@router.post("/chapters/questions", response_model=TaskResponseOut)
async def generate_qa(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to generate Q&A for a chapter."""
    task_id = services.task_registry.submit(
        _generate_qa_background, req.chapter, services
    )
    logger.info("Chapter questions task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="questions")


@router.post("/chapters/flashcards", response_model=TaskResponseOut)
async def generate_flashcards(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to generate flashcards for a chapter."""
    task_id = services.task_registry.submit(
        _generate_flashcards_background, req.chapter, services
    )
    logger.info("Chapter flashcards task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="flashcards")
