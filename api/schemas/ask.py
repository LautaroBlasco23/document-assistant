"""Q&A request/response schemas."""

from pydantic import BaseModel


class AskRequest(BaseModel):
    """Request to ask a question."""

    query: str
    book: str | None = None
    chapter: int | None = None
