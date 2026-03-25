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
    """Answer a question about a document or chapter using RAG.

    Retrieves relevant chunks via HybridRetriever, passes them to ChatAgent,
    and returns the LLM-generated answer synchronously.
    """
    # Build Qdrant filters
    filters: dict = {"file_hash": req.document_hash}
    if req.qdrant_index is not None:
        filters["chapter"] = req.qdrant_index
    elif req.chapter is not None:
        # Convert 1-based API chapter to 0-based Qdrant index
        filters["chapter"] = req.chapter - 1

    logger.info(
        "Chat request: doc=%s filters=%s query=%r",
        req.document_hash[:12],
        filters,
        req.query[:80],
    )

    # Retrieve relevant chunks
    chunks = services.retriever.retrieve(req.query, k=20, filters=filters)

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
