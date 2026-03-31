"""Configuration endpoints."""

import logging

from fastapi import APIRouter

from api.deps import ServicesDep
from api.schemas.config import (
    ChunkingConfigOut,
    ConfigOut,
    HuggingFaceConfigOut,
    Neo4jConfigOut,
    OllamaConfigOut,
    OpenRouterConfigOut,
    QdrantConfigOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config", response_model=ConfigOut)
async def get_config(services: ServicesDep) -> ConfigOut:
    """Get current configuration."""
    logger.info("Config read")
    config = services.config
    return ConfigOut(
        llm_provider=config.llm_provider,
        ollama=OllamaConfigOut(
            base_url=config.ollama.base_url,
            generation_model=config.ollama.generation_model,
            fast_model=config.ollama.fast_model,
            embedding_model=config.ollama.embedding_model,
            timeout=config.ollama.timeout,
        ),
        openrouter=OpenRouterConfigOut(
            base_url=config.openrouter.base_url,
            model=config.openrouter.model,
            fast_model=config.openrouter.fast_model,
            timeout=config.openrouter.timeout,
            max_retries=config.openrouter.max_retries,
        ),
        huggingface=HuggingFaceConfigOut(
            base_url=config.huggingface.base_url,
            model=config.huggingface.model,
            fast_model=config.huggingface.fast_model,
            timeout=config.huggingface.timeout,
            max_retries=config.huggingface.max_retries,
            wait_for_model=config.huggingface.wait_for_model,
        ),
        qdrant=QdrantConfigOut(
            url=config.qdrant.url,
            collection_name=config.qdrant.collection_name,
        ),
        neo4j=Neo4jConfigOut(
            uri=config.neo4j.uri,
            user=config.neo4j.user,
        ),
        chunking=ChunkingConfigOut(
            max_tokens=config.chunking.max_tokens,
            overlap_tokens=config.chunking.overlap_tokens,
        ),
    )


@router.put("/config", response_model=ConfigOut)
async def update_config(update: dict, services: ServicesDep) -> ConfigOut:
    """Update configuration and reload services."""
    # For now, this is a placeholder since dynamic config reload is complex
    # In a real implementation, you'd merge the update with current config and reinitialize services
    logger.info("Configuration update requested (not yet implemented)")
    return await get_config(services)
