from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Agent:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    name: str = ""
    prompt: str = ""
    model: str = ""
    provider: str = "groq"
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 1024
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
