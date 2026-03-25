from typing import Literal

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    document_hash: str
    chapter: int | None = None       # 1-based; None = whole document
    qdrant_index: int | None = None  # actual Qdrant chapter index (0-based)
    query: str
    history: list[ChatMessageIn] = []  # previous messages for multi-turn context


class ChatSourceOut(BaseModel):
    page_number: int | None = None
    text_preview: str  # first ~200 chars of the chunk


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSourceOut] = []
