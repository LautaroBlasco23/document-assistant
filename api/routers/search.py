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
    filters = None
    if req.chapter is not None:
        # Convert 1-based to 0-based
        filters = {"chapter": req.chapter - 1}

    try:
        chunks = services.retriever.retrieve(req.query, k=req.k, filters=filters)

        results = [
            ChunkOut(
                id=f"{c.file_hash[:12]}:{c.chapter}:{c.chunk_id}",
                text=c.text[:500],  # Truncate for display
                chapter=c.chapter + 1,  # Convert back to 1-based
                page=c.page,
                score=None,  # Score not available from hybrid retriever
            )
            for c in chunks
        ]

        return SearchResultsOut(query=req.query, chunks=results, count=len(results))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
