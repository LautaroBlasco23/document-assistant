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
    title: str
    content: str
    is_main: bool
    created_at: str
    updated_at: str


class KnowledgeChunkOut(BaseModel):
    id: str
    chunk_index: int
    text: str
    token_count: int
