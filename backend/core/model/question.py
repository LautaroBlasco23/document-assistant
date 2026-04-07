from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

QuestionType = Literal["true_false", "multiple_choice", "matching", "checkbox"]


@dataclass
class Question:
    tree_id: UUID
    chapter_id: UUID
    question_type: QuestionType
    question_data: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
