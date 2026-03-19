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
    statuses: list[ServiceStatus] = []

    # Check Ollama
    try:
        resp = requests.get(f"{services.embedder.base_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            statuses.append(ServiceStatus(name="ollama", healthy=True))
        else:
            statuses.append(
                ServiceStatus(name="ollama", healthy=False, error=f"HTTP {resp.status_code}")
            )
    except Exception as e:
        statuses.append(ServiceStatus(name="ollama", healthy=False, error=str(e)))

    # Check Qdrant
    try:
        health = services.qdrant.client.get_collection_info(services.qdrant.collection_name)
        statuses.append(ServiceStatus(name="qdrant", healthy=True))
    except Exception as e:
        statuses.append(ServiceStatus(name="qdrant", healthy=False, error=str(e)))

    # Check Neo4j
    try:
        with services.neo4j.driver.session() as session:
            session.run("RETURN 1")
        statuses.append(ServiceStatus(name="neo4j", healthy=True))
    except Exception as e:
        statuses.append(ServiceStatus(name="neo4j", healthy=False, error=str(e)))

    all_healthy = all(s.healthy for s in statuses)
    status = "healthy" if all_healthy else "degraded"

    return HealthOut(status=status, services=statuses)
