"""Chat endpoint for per-document / per-chapter Q&A."""

import logging

from fastapi import APIRouter

from api.deps import ServicesDep
from api.schemas.chat import ChatRequest, ChatResponse, ChatSourceOut
from application.agents.chat_agent import ChatAgent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, services: ServicesDep) -> ChatResponse:
    """Answer a question about a document or chapter.

    Fetches chunks directly from PostgreSQL, passes them to ChatAgent,
    and returns the LLM-generated answer synchronously.
    """
    # Determine chapter_index (0-based) from 1-based API field
    chapter_index: int | None = None
    if req.chapter is not None:
        chapter_index = req.chapter - 1

    logger.info(
        "Chat request: doc=%s chapter_index=%s query=%r",
        req.document_hash[:12],
        chapter_index,
        req.query[:80],
    )

    # Fetch chunks directly from PostgreSQL
    if chapter_index is not None:
        chunks = services.content_store.get_chunks_by_chapter(req.document_hash, chapter_index)
    else:
        chunks = services.content_store.get_chunks_by_file(req.document_hash)

    if not chunks:
        logger.info("No chunks found for chat request, returning fallback answer")
        return ChatResponse(
            answer="I couldn't find relevant information in this document to answer your question.",
            sources=[],
        )

    logger.info("Retrieved %d chunks for chat request", len(chunks))

    # Get document metadata for context (title, description)
    metadata = services.content_store.get_metadata(req.document_hash)
    document_title = metadata.description if metadata else ""

    # Determine chapter title if scoped
    chapter_title = ""
    if req.chapter is not None:
        chapter_title = f"Chapter {req.chapter}"

    # Build history as plain dicts for the agent
    history = [{"role": msg.role, "content": msg.content} for msg in req.history]

    # Use the main LLM (not fast_llm) for better answer quality
    agent = ChatAgent(services.llm)
    answer = agent.answer(
        query=req.query,
        chunks=chunks,
        history=history if history else None,
        document_title=document_title,
        chapter_title=chapter_title,
    )

    # Build sources from retrieved chunks
    sources = [
        ChatSourceOut(
            page_number=chunk.metadata.page_number if chunk.metadata else None,
            text_preview=chunk.text[:200],
        )
        for chunk in chunks
    ]

    return ChatResponse(answer=answer, sources=sources)
