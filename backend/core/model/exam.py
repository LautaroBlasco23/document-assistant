from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class ExamResult:
    id: str = field(default_factory=lambda: str(uuid4()))
    document_hash: str = ""
    chapter_index: int = 0       # 0-based internally
    total_cards: int = 0
    correct_count: int = 0
    passed: bool = False         # correct_count == total_cards
    completed_at: datetime = field(default_factory=datetime.utcnow)
