"""Document-related schemas."""

from pydantic import BaseModel, Field


class SectionOut(BaseModel):
    """Section metadata within a chapter."""

    title: str
    page_start: int
    page_end: int


class ChapterOut(BaseModel):
    """Chapter metadata."""

    number: int
    title: str | None
    num_chunks: int
    sections: list[SectionOut] = []


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
    num_chapters: int
    chapters: list[ChapterOut]


class IngestTaskOut(BaseModel):
    """Response from ingest endpoint with task tracking."""

    task_id: str
    filename: str


class MetadataRequest(BaseModel):
    """Request body for saving document metadata."""

    description: str = Field(
        default="",
        max_length=500,
        description="User-provided description of the document (max 500 chars)",
    )
    document_type: str = Field(
        default="",
        description="Type of document (book, paper, documentation, article, notes, other)",
    )


class MetadataResponse(BaseModel):
    """Response containing document metadata."""

    document_hash: str
    description: str
    document_type: str = ""
