"""Pydantic schemas for the Knowledge Tree API."""

from pydantic import BaseModel

# --- Requests ---


class CreateTreeRequest(BaseModel):
    title: str
    description: str | None = None


class CreateChapterRequest(BaseModel):
    title: str


class CreateDocumentRequest(BaseModel):
    title: str
    content: str
    chapter_id: str | None = None
    is_main: bool = False


class UpdateTreeRequest(BaseModel):
    title: str
    description: str | None = None


class UpdateChapterRequest(BaseModel):
    title: str


class UpdateDocumentRequest(BaseModel):
    title: str
    content: str


# --- Responses ---


class KnowledgeTreeOut(BaseModel):
    id: str
    title: str
    description: str | None
    num_chapters: int
    created_at: str


class KnowledgeChapterOut(BaseModel):
    id: str
    tree_id: str
    number: int
    title: str
    created_at: str


class KnowledgeDocumentOut(BaseModel):
    id: str
    tree_id: str
    chapter_id: str | None
    chapter_number: int | None = None
    title: str
    content: str
    is_main: bool
    created_at: str
    updated_at: str
    source_file_path: str | None = None
    source_file_name: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class KnowledgeChunkOut(BaseModel):
    id: str
    chunk_index: int
    text: str
    token_count: int


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


# --- Exam Sessions ---


class CreateExamSessionRequest(BaseModel):
    score: float
    total_questions: int
    correct_count: int
    question_ids: list[str]
    results: dict[str, bool]


class ExamSessionOut(BaseModel):
    id: str
    tree_id: str
    chapter_id: str
    score: float
    total_questions: int
    correct_count: int
    question_ids: list[str]
    results: dict[str, bool]
    created_at: str
