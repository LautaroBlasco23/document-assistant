"""Health check endpoints."""

import logging

import requests
from fastapi import APIRouter

from api.deps import ServicesDep
from api.schemas.health import HealthOut, ServiceStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def get_health(services: ServicesDep) -> HealthOut:
    """Check health of all external services."""
    logger.debug("Health check requested")
    statuses: list[ServiceStatus] = []

    # Check LLM provider connectivity
    if services.config.llm_provider == "ollama":
        try:
            resp = requests.get(
                f"{services.config.ollama.base_url.rstrip('/')}/api/tags", timeout=3
            )
            if resp.status_code == 200:
                statuses.append(ServiceStatus(name="llm", healthy=True))
            else:
                statuses.append(
                    ServiceStatus(name="llm", healthy=False, error=f"HTTP {resp.status_code}")
                )
        except Exception as e:
            statuses.append(ServiceStatus(name="llm", healthy=False, error=str(e)))
    else:
        # Groq, OpenRouter, HuggingFace — check that API key is set
        api_key = services.config.groq.api_key if hasattr(services.config, "groq") else ""
        if api_key:
            statuses.append(ServiceStatus(name="llm", healthy=True))
        else:
            statuses.append(
                ServiceStatus(name="llm", healthy=False, error="API key not set")
            )

    # Check PostgreSQL
    try:
        with services._pg_pool.connection().cursor() as cur:
            cur.execute("SELECT 1")
        statuses.append(ServiceStatus(name="postgres", healthy=True))
    except Exception as e:
        statuses.append(ServiceStatus(name="postgres", healthy=False, error=str(e)))

    all_healthy = all(s.healthy for s in statuses)
    status = "healthy" if all_healthy else "degraded"

    return HealthOut(status=status, services=statuses)
