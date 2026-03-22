from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Summary:
    document_hash: str
    chapter_index: int          # 0-based internally
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QAPair:
    id: str = field(default_factory=lambda: str(uuid4()))
    document_hash: str = ""
    chapter_index: int = 0      # 0-based internally
    question: str = ""
    answer: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Flashcard:
    id: str = field(default_factory=lambda: str(uuid4()))
    document_hash: str = ""
    chapter_index: int = 0      # 0-based internally
    front: str = ""
    back: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
