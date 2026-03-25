"""Stored content retrieval endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from api.deps import ServicesDep
from api.schemas.content import (
    FlashcardBulkActionRequest,
    FlashcardResponse,
    SummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents/{file_hash}/summaries", response_model=list[SummaryResponse])
async def get_summaries(file_hash: str, services: ServicesDep) -> list[SummaryResponse]:
    """Get all stored summaries for a document."""
    summaries = services.content_store.get_summaries(file_hash)
    return [
        SummaryResponse(
            chapter=s.chapter_index + 1,
            content=s.content,
            description=s.description,
            bullets=s.bullets,
            created_at=s.created_at.isoformat(),
        )
        for s in summaries
    ]


@router.get("/documents/{file_hash}/summaries/{chapter}", response_model=SummaryResponse)
async def get_summary(file_hash: str, chapter: int, services: ServicesDep) -> SummaryResponse:
    """Get summary for a specific chapter (1-based)."""
    summary = services.content_store.get_summary(file_hash, chapter - 1)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return SummaryResponse(
        chapter=chapter,
        content=summary.content,
        description=summary.description,
        bullets=summary.bullets,
        created_at=summary.created_at.isoformat(),
    )


@router.delete("/documents/{file_hash}/summaries/{chapter}", status_code=204)
async def delete_summary(file_hash: str, chapter: int, services: ServicesDep) -> None:
    """Delete the stored summary for a specific chapter (1-based)."""
    services.content_store.delete_summary(file_hash, chapter - 1)


@router.get("/documents/{file_hash}/flashcards", response_model=list[FlashcardResponse])
async def get_flashcards(
    file_hash: str,
    services: ServicesDep,
    chapter: int | None = None,
    status: str | None = "approved",
) -> list[FlashcardResponse]:
    """Get flashcards. Optional chapter filter (1-based).
    By default returns only approved cards. Pass ?status=pending to see pending cards."""
    chapter_index = (chapter - 1) if chapter is not None else None
    # Normalize "all" to None so the repository returns all regardless of status
    status_filter = None if status == "all" else status
    cards = services.content_store.get_flashcards(file_hash, chapter_index, status=status_filter)
    return [
        FlashcardResponse(
            id=c.id,
            chapter=c.chapter_index + 1,
            front=c.front,
            back=c.back,
            source_page=c.source_page,
            source_chunk_id=c.source_chunk_id,
            source_text=c.source_text,
            status=c.status,
            created_at=c.created_at.isoformat(),
        )
        for c in cards
    ]


@router.patch("/documents/{file_hash}/flashcards/approve", status_code=200)
async def approve_flashcards(
    file_hash: str,
    body: FlashcardBulkActionRequest,
    services: ServicesDep,
) -> dict:
    """Bulk-update flashcard status to 'approved'."""
    count = services.content_store.approve_flashcards(body.flashcard_ids)
    return {"approved": count}


@router.delete("/documents/{file_hash}/flashcards/reject", status_code=200)
async def reject_flashcards(
    file_hash: str,
    body: FlashcardBulkActionRequest,
    services: ServicesDep,
) -> dict:
    """Hard-delete rejected cards from the database."""
    count = services.content_store.delete_flashcards_by_ids(body.flashcard_ids)
    return {"deleted": count}


@router.post("/documents/{file_hash}/flashcards/approve-all", status_code=200)
async def approve_all_flashcards(
    file_hash: str,
    services: ServicesDep,
    chapter: int | None = None,
) -> dict:
    """Approve all pending flashcards for a document (optional chapter filter, 1-based)."""
    chapter_index = (chapter - 1) if chapter is not None else None
    count = services.content_store.approve_all_flashcards(file_hash, chapter_index)
    return {"approved": count}
