"""Shared chapter resolution and context helpers."""

from uuid import UUID

from fastapi import HTTPException

from api.services import Services
from application.agents._batching import chunks_around_selection
from application.agents._tokens import truncate_tokens


def parse_uuid(value: str, label: str) -> UUID:
    """Parse a UUID string or raise HTTPException 422."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid {label}: {value}")


def resolve_chapter(services: Services, tree_id: str, number: int) -> tuple[UUID, object]:
    """Resolve (tree_uid, chapter) or raise 404."""
    uid = parse_uuid(tree_id, "tree_id")
    if services.kt_tree_store.get_tree(uid) is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    chapter = next(
        (c for c in services.kt_chapter_store.list_chapters(uid) if c.number == number), None
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")
    return uid, chapter


def get_chapter_context(
    services: Services,
    tree_id: UUID,
    number: int,
    selected_text: str = "",
    max_tokens: int = 4000,
) -> str:
    """Get chapter chunks around selected text, truncated to max_tokens."""
    chunks = services.kt_content_store.get_chunks(tree_id, number)
    window = chunks_around_selection(chunks, selected_text, neighbors=1)
    joined = "\n\n".join(c.text for c in window if c.text)
    return truncate_tokens(joined, max_tokens)
