from pydantic import BaseModel


class SubmitExamRequest(BaseModel):
    document_hash: str
    chapter: int              # 1-based (API convention)
    total_cards: int
    correct_count: int


class ExamResultOut(BaseModel):
    id: str
    chapter: int              # 1-based
    total_cards: int
    correct_count: int
    passed: bool
    completed_at: str         # ISO 8601


class ChapterExamStatusOut(BaseModel):
    chapter: int              # 1-based
    level: int                # 0-3
    level_name: str           # "none" | "completed" | "gold" | "platinum"
    last_exam_at: str | None  # ISO 8601 or null
    cooldown_until: str | None  # ISO 8601 or null
    can_take_exam: bool       # true if cooldown has passed
