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
                task.result = {"chapter": chapter_num, "summary": cached.content, "cached": True}
                logger.info("Returning cached summary for chapter %d", chapter_num)
                return cached.content

        task.progress = f"Retrieving context for chapter {chapter_num}..."
        chunks = services.retriever.retrieve(
            f"chapter {chapter_num} summary", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        task.progress = "Generating summary..."
        chapter_obj = Chapter(index=chapter_index, title=f"Chapter {chapter_num}", pages=[])
        summary = SummarizerAgent(services.fast_llm).summarize(chapter_obj, chunks)

        services.content_store.save_summary(
            Summary(document_hash=document_hash, chapter_index=chapter_index, content=summary)
        )

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
                task.result = {"chapter": chapter_num, "qa_pairs": qas, "cached": True}
                logger.info("Returning cached Q&A for chapter %d", chapter_num)
                return qas

        task.progress = f"Retrieving context for chapter {chapter_num}..."
        chunks = services.retriever.retrieve(
            f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        task.progress = "Generating Q&A..."
        qas = QuestionGeneratorAgent(services.fast_llm).generate(chunks)

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
                task.result = {"chapter": chapter_num, "flashcards": flashcards, "cached": True}
                logger.info("Returning cached flashcards for chapter %d", chapter_num)
                return flashcards

        task.progress = f"Retrieving context for chapter {chapter_num}..."
        chunks = services.retriever.retrieve(
            f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
        )

        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        task.progress = "Generating flashcards..."
        # Flashcards are similar to Q&A, so reuse the generator
        qas = QuestionGeneratorAgent(services.fast_llm).generate(chunks)

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
