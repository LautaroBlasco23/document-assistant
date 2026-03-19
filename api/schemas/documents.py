"""Document-related schemas."""

from pydantic import BaseModel


class ChapterOut(BaseModel):
    """Chapter metadata."""

    number: int
    title: str | None
    num_chunks: int


class DocumentOut(BaseModel):
    """Document metadata."""

    file_hash: str
    filename: str
    num_chapters: int
    chapters: list[ChapterOut] | None = None  # Only populated by structure endpoint


class DocumentStructureOut(BaseModel):
    """Full document structure with chapters."""

    file_hash: str
    filename: str
    chapters: list[ChapterOut]


class IngestTaskOut(BaseModel):
    """Response from ingest endpoint with task tracking."""

    task_id: str
    filename: str
