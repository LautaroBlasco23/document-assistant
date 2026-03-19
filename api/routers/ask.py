"""Q&A endpoints with streaming."""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import ServicesDep
from api.schemas.ask import AskRequest
from api.streaming import make_sse_event
from application.agents.qa_agent import QAAgent

logger = logging.getLogger(__name__)

router = APIRouter()


async def _stream_answer(
    query: str, filters: dict | None, services: ServicesDep
) -> AsyncGenerator[str, None]:
    """Stream Q&A answer tokens."""
    try:
        # Run retrieval in thread pool (sync operation)
        chunks = await asyncio.to_thread(
            services.retriever.retrieve, query, 20, filters
        )

        if not chunks:
            yield make_sse_event("error", {"message": "No relevant context found"})
            yield make_sse_event("done", {"full_answer": ""})
            return

        # Prepare context
        context = "\n\n".join(f"[{c.chapter}:{c.chunk_id}] {c.text}" for c in chunks)

        # Build system and user prompts
        system_prompt = (
            "You are a helpful assistant answering questions based on provided documents. "
            "Be concise and cite the source when relevant."
        )
        user_prompt = f"Context:\n{context}\n\nQuestion: {query}"

        # For now, use the regular chat (not streaming) since ollama.chat_stream doesn't exist yet
        # TODO: Add chat_stream to OllamaLLM for token-by-token streaming
        full_answer = services.llm.chat(system_prompt, user_prompt)

        # Emit the full answer as a single event (fallback)
        yield make_sse_event("token", {"token": full_answer})
        yield make_sse_event("done", {"full_answer": full_answer})

    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        yield make_sse_event("error", {"message": str(e)})


@router.post("/ask")
async def ask_question(req: AskRequest, services: ServicesDep) -> StreamingResponse:
    """Ask a question with SSE streaming response."""
    filters = None
    if req.chapter is not None:
        # Convert 1-based to 0-based
        filters = {"chapter": req.chapter - 1}

    return StreamingResponse(
        _stream_answer(req.query, filters, services),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
