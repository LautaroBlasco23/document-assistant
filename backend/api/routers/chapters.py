"""Chapter analysis endpoints."""

import json
import logging
import time

from fastapi import APIRouter

from api.deps import ServicesDep
from api.schemas.chapters import ChapterRequest, TaskResponseOut
from api.tasks import Task
from application.agents.flashcard_generator import FlashcardGeneratorAgent
from application.agents.summarizer import SummarizerAgent
from core.model.document import Chapter
from core.model.generated_content import Flashcard, Summary
from infrastructure.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

router = APIRouter()

_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def _set_progress(task: Task, pct: int, message: str) -> None:
    """Set both numeric and text progress on a task."""
    task.progress_pct = max(0, min(100, pct))
    task.progress = message
    logger.debug("Progress [%d%%]: %s", task.progress_pct, message)


def _get_document_title(document_hash: str) -> str:
    """Look up document title from its manifest file."""
    if not _OUTPUT_DIR.exists():
        return ""
    for doc_dir in _OUTPUT_DIR.iterdir():
        if not doc_dir.is_dir():
            continue
        manifest_file = doc_dir / "manifest.json"
        if not manifest_file.exists():
            continue
        try:
            with open(manifest_file) as f:
                manifest = json.load(f)
            if manifest.get("file_hash") == document_hash:
                return manifest.get("title", "")
        except Exception:
            continue
    return ""


def _summarize_background(
    task: Task,
    chapter_num: int,
    qdrant_index: int,
    services: ServicesDep,
    document_hash: str,
    force: bool,
) -> str:
    """Background task to summarize a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting summarize for chapter %d (qdrant_index=%d)", chapter_num, qdrant_index)
    try:
        # Return cached result if available and not forced
        if not force:
            cached = services.content_store.get_summary(document_hash, qdrant_index)
            if cached:
                _set_progress(task, 100, "Loaded from cache")
                task.result = {
                    "chapter": chapter_num,
                    "description": cached.description,
                    "bullets": cached.bullets,
                    "cached": True,
                }
                logger.info("Returning cached summary for chapter %d", chapter_num)
                return cached.content

        document_title = _get_document_title(document_hash)
        _metadata = services.content_store.get_metadata(document_hash)
        document_description = _metadata.description if _metadata else ""
        document_type = _metadata.document_type if _metadata else ""

        _set_progress(task, 10, f"Retrieving context for chapter {chapter_num}...")
        chunks = services.qdrant.search_by_chapter(document_hash, qdrant_index)

        if not chunks:
            logger.error(
                "No chunks found: file_hash=%s, chapter_index=%d (1-based chapter=%d)",
                document_hash,
                qdrant_index,
                chapter_num,
            )
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        chunks.sort(key=lambda c: (c.metadata.page_number if c.metadata else 0))

        logger.info(
            "Retrieved %d chunks for chapter %d (doc=%s)",
            len(chunks),
            chapter_num,
            document_hash[:12],
        )
        _set_progress(task, 25, f"Retrieved {len(chunks)} chunks, generating summary...")
        chapter_title = f"Chapter {chapter_num}"
        chapter_obj = Chapter(index=qdrant_index, title=chapter_title, pages=[])

        def sum_progress(phase: str) -> None:
            if phase == "calling_llm":
                _set_progress(task, 40, "LLM is generating summary...")

        summary = SummarizerAgent(services.fast_llm).summarize(
            chapter_obj,
            chunks,
            on_progress=sum_progress,
            document_title=document_title,
            document_description=document_description,
            document_type=document_type,
        )

        _set_progress(task, 85, "Saving summary...")
        services.content_store.save_summary(
            Summary(
                document_hash=document_hash,
                chapter_index=qdrant_index,
                content=summary["content"],
                description=summary["description"],
                bullets=summary["bullets"],
            )
        )
        logger.debug("Persisted summary for doc=%s chapter=%d", document_hash[:12], qdrant_index)

        _set_progress(task, 95, "Finalizing...")
        task.result = {
            "chapter": chapter_num,
            "description": summary["description"],
            "bullets": summary["bullets"],
            "cached": False,
        }
        elapsed = time.perf_counter() - t0
        logger.info("Completed summarize for chapter %d in %.1fs", chapter_num, elapsed)
        return summary["content"]
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise


def _generate_flashcards_background(
    task: Task,
    chapter_num: int,
    qdrant_index: int,
    services: ServicesDep,
    document_hash: str,
    force: bool,
) -> list[dict]:
    """Background task to generate flashcards for a chapter."""
    t0 = time.perf_counter()
    logger.info("Starting flashcards for chapter %d (qdrant_index=%d)", chapter_num, qdrant_index)
    try:
        # Return cached result if available and not forced
        if not force:
            cached = services.content_store.get_flashcards(document_hash, qdrant_index)
            if cached:
                flashcards = [
                    {
                        "id": c.id,
                        "front": c.front,
                        "back": c.back,
                        "category": "key_facts",
                        "source_page": c.source_page,
                        "source_text": c.source_text,
                    }
                    for c in cached
                ]
                _set_progress(task, 100, "Loaded from cache")
                task.result = {"chapter": chapter_num, "flashcards": flashcards, "cached": True}
                logger.info("Returning cached flashcards for chapter %d", chapter_num)
                return flashcards

        document_title = _get_document_title(document_hash)
        _metadata = services.content_store.get_metadata(document_hash)
        document_description = _metadata.description if _metadata else ""
        document_type = _metadata.document_type if _metadata else ""
        chapter_title = f"Chapter {chapter_num}"

        _set_progress(task, 5, f"Retrieving context for chapter {chapter_num}...")
        chunks = services.qdrant.search_by_chapter(document_hash, qdrant_index)

        if not chunks:
            logger.error(
                "No chunks found: file_hash=%s, chapter_index=%d (1-based chapter=%d)",
                document_hash,
                qdrant_index,
                chapter_num,
            )
            raise ValueError(f"No chunks found for chapter {chapter_num}")

        chunks.sort(key=lambda c: (c.metadata.page_number if c.metadata else 0))

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

        # Select LLM for flashcard generation based on config
        if services.config.flashcard_model == "fast" and services.config.llm_provider == "openrouter":
            logger.warning(
                "flashcard_model=fast is not viable for openrouter (model too small); "
                "falling back to main model"
            )
            flashcard_llm = services.llm
        elif services.config.flashcard_model == "fast":
            flashcard_llm = services.fast_llm
        else:
            flashcard_llm = services.llm

        # Fetch existing chapter summary to give the model context
        existing_summary = services.content_store.get_summary(document_hash, qdrant_index)
        chapter_summary_text = ""
        if existing_summary:
            bullets_str = "\n".join(f"- {b}" for b in existing_summary.bullets) if existing_summary.bullets else ""
            chapter_summary_text = f"{existing_summary.description}\n{bullets_str}".strip()
        else:
            logger.debug(
                "No summary found for doc=%s chapter=%d; "
                "consider summarizing first for better flashcard quality",
                document_hash[:12],
                qdrant_index,
            )

        cards = FlashcardGeneratorAgent(flashcard_llm).generate(
            chunks,
            on_progress=fc_progress,
            chapter_title=chapter_title,
            document_title=document_title,
            document_description=document_description,
            document_type=document_type,
            chapter_summary=chapter_summary_text,
        )

        # Build page -> chunks lookup for source attribution
        page_to_chunks: dict[int, list] = {}
        for chunk in chunks:
            page = chunk.metadata.page_number if chunk.metadata else None
            if page is not None:
                page_to_chunks.setdefault(page, []).append(chunk)

        _set_progress(task, 85, "Saving flashcards...")
        flashcard_models = []
        for card in cards:
            source_page = card.get("source_page")
            source_chunk_id = ""
            source_text = ""
            if source_page is not None:
                matching = page_to_chunks.get(source_page, [])
                if matching:
                    best_chunk = matching[0]
                    source_chunk_id = best_chunk.id or ""
                    source_text = (best_chunk.text or "")[:400]
            flashcard_models.append(
                Flashcard(
                    document_hash=document_hash,
                    chapter_index=qdrant_index,
                    front=card["front"],
                    back=card["back"],
                    source_page=source_page,
                    source_chunk_id=source_chunk_id,
                    source_text=source_text,
                    status="pending",
                )
            )
        services.content_store.save_flashcards(flashcard_models)
        logger.debug(
            "Persisted %d flashcards (pending) for doc=%s chapter=%d",
            len(flashcard_models),
            document_hash[:12],
            qdrant_index,
        )
        services.content_store.reset_exam_progress(document_hash, qdrant_index)
        logger.debug("Reset exam progress for doc=%s chapter=%d", document_hash[:12], qdrant_index)

        _set_progress(task, 95, "Finalizing...")
        task.result = {
            "chapter": chapter_num,
            "flashcards": [
                {
                    "id": card_model.id,
                    "front": card["front"],
                    "back": card["back"],
                    "category": card.get("category", "key_facts"),
                    "source_page": card.get("source_page"),
                    "source_text": card_model.source_text,
                }
                for card, card_model in zip(cards, flashcard_models)
            ],
            "cached": False,
        }
        elapsed = time.perf_counter() - t0
        logger.info("Completed flashcards for chapter %d in %.1fs", chapter_num, elapsed)
        return cards
    except Exception as e:
        logger.error(f"Flashcard generation failed: {e}")
        raise


@router.post("/chapters/summarize", response_model=TaskResponseOut)
async def summarize_chapter(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to summarize a chapter."""
    task_id = services.task_registry.submit(
        _summarize_background,
        req.chapter,
        req.qdrant_index,  # Pass actual Qdrant chapter_index for filtering
        services,
        req.document_hash,
        req.force,
        task_type="summarize",
        doc_hash=req.document_hash,
        chapter=req.chapter,
        book_title=req.book_title,
    )
    logger.info("Chapter summarize task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="summarize")


@router.post("/chapters/flashcards", response_model=TaskResponseOut)
async def generate_flashcards(req: ChapterRequest, services: ServicesDep) -> TaskResponseOut:
    """Start background task to generate flashcards for a chapter."""
    task_id = services.task_registry.submit(
        _generate_flashcards_background,
        req.chapter,
        req.qdrant_index,  # Pass actual Qdrant chapter_index for filtering
        services,
        req.document_hash,
        req.force,
        task_type="flashcards",
        doc_hash=req.document_hash,
        chapter=req.chapter,
        book_title=req.book_title,
    )
    logger.info("Chapter flashcards task submitted: task_id=%s, chapter=%d", task_id, req.chapter)
    return TaskResponseOut(task_id=task_id, task_type="flashcards")
