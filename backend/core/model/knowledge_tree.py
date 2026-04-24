from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class KnowledgeTree:
    id: UUID
    user_id: UUID  # Owner reference
    title: str
    description: str | None
    created_at: datetime


@dataclass
class KnowledgeChapter:
    id: UUID
    tree_id: UUID
    number: int  # 1-based, user-facing
    title: str
    created_at: datetime


@dataclass
class KnowledgeDocument:
    id: UUID
    tree_id: UUID
    chapter_id: UUID | None  # None = tree-level
    title: str
    content: str
    is_main: bool
    created_at: datetime
    updated_at: datetime
    source_file_path: str | None = None
    source_file_name: str | None = None
    chapter_number: int | None = None
    page_start: int | None = None
    page_end: int | None = None


@dataclass
class Flashcard:
    id: UUID
    tree_id: UUID
    chapter_id: UUID
    doc_id: UUID | None
    front: str
    back: str
    source_text: str | None
    created_at: datetime


@dataclass
class KnowledgeChunk:
    id: UUID
    tree_id: UUID
    chapter_id: UUID
    doc_id: UUID
    chunk_index: int
    text: str
    token_count: int
