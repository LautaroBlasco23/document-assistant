from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

QuestionTypeLiteral = Literal["true_false", "multiple_choice", "matching", "checkbox"]


class QuestionOut(BaseModel):
    id: UUID
    question_type: QuestionTypeLiteral
    question_data: dict[str, Any]
    created_at: datetime


class GenerateQuestionsRequest(BaseModel):
    question_types: list[QuestionTypeLiteral] | None = None
    model: str | None = None
    num_questions: int | None = None
