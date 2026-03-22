from pydantic import BaseModel


class SummaryResponse(BaseModel):
    chapter: int        # 1-based (API convention)
    content: str
    created_at: str     # ISO 8601


class QAPairResponse(BaseModel):
    id: str
    chapter: int        # 1-based
    question: str
    answer: str
    created_at: str


class FlashcardResponse(BaseModel):
    id: str
    chapter: int        # 1-based
    front: str
    back: str
    created_at: str
