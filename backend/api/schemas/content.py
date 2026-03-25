from pydantic import BaseModel


class SummaryResponse(BaseModel):
    chapter: int        # 1-based (API convention)
    content: str
    description: str = ""
    bullets: list[str] = []
    created_at: str     # ISO 8601


class FlashcardResponse(BaseModel):
    id: str
    chapter: int        # 1-based
    front: str
    back: str
    source_page: int | None = None
    source_chunk_id: str = ""
    source_text: str = ""
    status: str = "pending"
    created_at: str


class FlashcardBulkActionRequest(BaseModel):
    flashcard_ids: list[str]
