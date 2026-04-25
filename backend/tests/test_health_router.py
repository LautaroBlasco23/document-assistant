"""
Unit tests for the health check router (/api/health).

Subject: api/routers/health.py
Scope:   GET /api/health — aggregate service health (LLM + PostgreSQL).
Out of scope:
  - Actual LLM HTTP behavior                 → respective LLM provider tests
  - Postgres connection internals            → test_postgres.py (integration)
Setup:   FastAPI TestClient with mocked services; requests.get is patched for
          Ollama provider health checks.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import get_services_dep
from api.routers import health as health_router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_services(llm_provider="groq", api_key="", ollama_base_url="http://localhost:11434"):
    """Return a mocked Services object configured for the given LLM provider."""
    services = MagicMock()
    services.config.llm_provider = llm_provider
    services.config.ollama.base_url = ollama_base_url
    services.config.groq.api_key = api_key
    services._pg_pool = MagicMock()
    return services


@pytest.fixture
def test_client():
    """Return a factory that builds a TestClient with arbitrary mocked services."""
    def _build(services):
        app = FastAPI()
        app.include_router(health_router.router, prefix="/api")
        app.dependency_overrides[get_services_dep] = lambda: services
        return TestClient(app)
    return _build


# ---------------------------------------------------------------------------
# All healthy
# ---------------------------------------------------------------------------


def test_health_all_healthy_groq(test_client):
    """When Groq API key is set and Postgres is up, health must be 200/healthy."""
    services = _make_services(llm_provider="groq", api_key="sk-test")
    client = test_client(services)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    services_names = {s["name"]: s["healthy"] for s in body["services"]}
    assert services_names["llm"] is True
    assert services_names["postgres"] is True


def test_health_all_healthy_ollama(test_client):
    """When Ollama responds 200 and Postgres is up, health must be 200/healthy."""
    services = _make_services(llm_provider="ollama")
    client = test_client(services)

    with patch("api.routers.health.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    mock_get.assert_called_once_with(
        "http://localhost:11434/api/tags", timeout=3
    )


# ---------------------------------------------------------------------------
# LLM down
# ---------------------------------------------------------------------------


def test_health_llm_unhealthy_ollama_500(test_client):
    """An Ollama HTTP 500 must be reflected as unhealthy LLM status."""
    services = _make_services(llm_provider="ollama")
    client = test_client(services)

    with patch("api.routers.health.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=500)
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    llm_status = next(s for s in body["services"] if s["name"] == "llm")
    assert llm_status["healthy"] is False
    assert "500" in llm_status["error"]


def test_health_llm_unhealthy_ollama_connection_error(test_client):
    """A connection refused to Ollama must be reflected as unhealthy LLM."""
    services = _make_services(llm_provider="ollama")
    client = test_client(services)

    with patch("api.routers.health.requests.get") as mock_get:
        mock_get.side_effect = ConnectionError("refused")
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    llm_status = next(s for s in body["services"] if s["name"] == "llm")
    assert llm_status["healthy"] is False
    assert "refused" in llm_status["error"]


def test_health_llm_unhealthy_groq_missing_key(test_client):
    """An empty Groq API key must be reflected as unhealthy LLM status."""
    services = _make_services(llm_provider="groq", api_key="")
    client = test_client(services)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    llm_status = next(s for s in body["services"] if s["name"] == "llm")
    assert llm_status["healthy"] is False
    assert "API key not set" in llm_status["error"]


# ---------------------------------------------------------------------------
# PostgreSQL down
# ---------------------------------------------------------------------------


def test_health_postgres_unhealthy(test_client):
    """A PostgreSQL connection failure must be reflected as unhealthy PG status."""
    services = _make_services(llm_provider="groq", api_key="sk-test")
    services._pg_pool.connection.return_value.cursor.side_effect = RuntimeError(
        "connection failed"
    )
    client = test_client(services)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    pg_status = next(s for s in body["services"] if s["name"] == "postgres")
    assert pg_status["healthy"] is False
    assert "connection failed" in pg_status["error"]


# ---------------------------------------------------------------------------
# Both down
# ---------------------------------------------------------------------------


def test_health_both_unhealthy(test_client):
    """When both LLM and Postgres are down, status must be degraded with both errors."""
    services = _make_services(llm_provider="groq", api_key="")
    services._pg_pool.connection.return_value.cursor.side_effect = RuntimeError("pg down")
    client = test_client(services)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    services_names = {s["name"]: s["healthy"] for s in body["services"]}
    assert services_names["llm"] is False
    assert services_names["postgres"] is False
