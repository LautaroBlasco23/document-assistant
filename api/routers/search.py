"""Search endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from api.deps import ServicesDep
from api.schemas.search import SearchRequest, SearchResultsOut, ChunkOut

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResultsOut)
async def search(req: SearchRequest, services: ServicesDep) -> SearchResultsOut:
    """Hybrid search across documents."""
    filters: dict | None = None
    if req.chapter is not None:
        # Convert 1-based to 0-based
        filters = {"chapter": req.chapter - 1}

    if req.book:
        filters = filters or {}
        filters["file_hash"] = req.book

    try:
        chunks = services.retriever.retrieve(req.query, k=req.k, filters=filters)

        results = []
        for c in chunks:
            src = c.metadata.source_file if c.metadata else ""
            ch = c.metadata.chapter_index if c.metadata else 0
            pg = c.metadata.page_number if c.metadata else None
            results.append(
                ChunkOut(
                    id=f"{src[:12]}:{ch}:{c.id}",
                    text=c.text[:500],
                    chapter=ch + 1,  # Convert to 1-based
                    page=pg,
                    score=c.score,
                )
            )

        return SearchResultsOut(query=req.query, chunks=results, count=len(results))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
