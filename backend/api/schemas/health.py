"""Health check schemas."""

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Status of a single external service."""

    name: str
    healthy: bool
    error: str | None = None


class HealthOut(BaseModel):
    """Health check response."""

    status: str  # "healthy" or "degraded"
    services: list[ServiceStatus]
