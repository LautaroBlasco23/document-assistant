from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class LLMCredential:
    id: UUID
    user_id: UUID
    provider: str
    api_key_last4: str | None
    last_tested_at: datetime | None
    last_test_ok: bool | None
    last_test_error: str | None
    created_at: datetime
    updated_at: datetime
