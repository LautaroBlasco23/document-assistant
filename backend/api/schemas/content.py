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
    created_at: str
