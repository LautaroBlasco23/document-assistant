"""Chapter analysis schemas."""

from pydantic import BaseModel


class ChapterRequest(BaseModel):
    """Request for chapter analysis."""

    book_title: str  # Used for context only
    chapter: int  # 1-based user-facing number
    chapter_index: int  # 0-based chapter index stored in PostgreSQL
    document_hash: str  # SHA-256 file hash for persistence
    force: bool = False  # Force regeneration even if cached


class TaskResponseOut(BaseModel):
    """Response from starting an async task."""

    task_id: str
    task_type: str


class SummaryOut(BaseModel):
    """Chapter summary."""

    chapter: int
    summary: str


class QAPairOut(BaseModel):
    """Q&A pair."""

    question: str
    answer: str


class FlashcardOut(BaseModel):
    """Flashcard."""

    question: str
    answer: str
