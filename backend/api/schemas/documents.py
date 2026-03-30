"""Document-related schemas."""

from pydantic import BaseModel, Field


class SectionOut(BaseModel):
    """Section metadata within a chapter."""

    title: str
    page_start: int
    page_end: int


class ChapterOut(BaseModel):
    """Chapter metadata."""

    number: int  # User-facing sequential number (1, 2, 3...)
    qdrant_index: int  # Actual chapter_index stored in Qdrant (may have gaps)
    title: str | None
    num_chunks: int
    sections: list[SectionOut] = []
    toc_href: str = ""  # EPUB TOC href for direct viewer navigation (empty for PDFs)


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
    file_extension: str = ""


class ChapterDeleteResponse(BaseModel):
    """Response from chapter deletion endpoint."""

    message: str
    vectors_deleted: int
    summaries_deleted: int
    flashcards_deleted: int


class ChapterPreviewOut(BaseModel):
    """Chapter metadata for preview/selection."""

    index: int
    title: str
    page_start: int
    page_end: int


class DocumentPreviewOut(BaseModel):
    """Response from preview endpoint - chapter structure without storage."""

    file_hash: str
    filename: str
    num_chapters: int
    chapters: list[ChapterPreviewOut]


class IngestChaptersRequest(BaseModel):
    """Request to ingest selected chapters after preview."""

    chapter_indices: list[int] = Field(description="0-based indices of chapters to ingest")
    document_type: str = Field(default="")
    description: str = Field(default="")
