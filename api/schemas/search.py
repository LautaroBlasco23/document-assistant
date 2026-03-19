"""Search request/response schemas."""

from pydantic import BaseModel


class SearchRequest(BaseModel):
    """Request to search documents."""

    query: str
    book: str | None = None  # Filter by book name (unused for now)
    chapter: int | None = None  # Filter by chapter (1-based)
    k: int = 20  # Number of results


class ChunkOut(BaseModel):
    """A retrieved chunk."""

    id: str
    text: str
    chapter: int
    page: int | None = None
    score: float | None = None


class SearchResultsOut(BaseModel):
    """Search results."""

    query: str
    chunks: list[ChunkOut]
    count: int
