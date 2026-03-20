"""Q&A endpoints with streaming."""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.deps import ServicesDep
from api.schemas.ask import AskRequest
from api.streaming import make_sse_event

logger = logging.getLogger(__name__)

router = APIRouter()


async def _stream_answer(
    query: str, filters: dict | None, services: ServicesDep
) -> AsyncGenerator[str, None]:
    """Stream Q&A answer tokens, then emit sources."""
    try:
        # Run retrieval in thread pool (sync operation)
        chunks = await asyncio.to_thread(
            services.retriever.retrieve, query, 20, filters
        )

        if not chunks:
            yield make_sse_event("error", {"message": "No relevant context found"})
            yield make_sse_event("done", {"sources": []})
            return

        # Prepare context using metadata fields
        context = "\n\n".join(
            f"[{c.metadata.chapter_index if c.metadata else 0}:{c.id}] {c.text}"
            for c in chunks
        )

        # Build system and user prompts
        system_prompt = (
            "You are a helpful assistant answering questions based on provided documents. "
            "Be concise and cite the source when relevant."
        )
        user_prompt = f"Context:\n{context}\n\nQuestion: {query}"

        # Stream tokens via chat_stream (sync generator run in thread pool)
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _produce():
            try:
                for token in services.llm.chat_stream(system_prompt, user_prompt):
                    loop.call_soon_threadsafe(token_queue.put_nowait, token)
            finally:
                loop.call_soon_threadsafe(token_queue.put_nowait, None)

        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop.run_in_executor(executor, _produce)

        while True:
            token = await token_queue.get()
            if token is None:
                break
            yield make_sse_event("token", {"token": token})

        # Format sources
        sources = []
        for c in chunks:
            src = c.metadata.source_file if c.metadata else ""
            ch = c.metadata.chapter_index if c.metadata else 0
            pg = c.metadata.page_number if c.metadata else None
            sources.append(
                {
                    "id": f"{src[:12]}:{ch}:{c.id}",
                    "text": c.text[:500],
                    "chapter": ch + 1,  # Convert to 1-based
                    "page": pg,
                    "score": c.score,
                }
            )
        yield make_sse_event("done", {"sources": sources})

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
