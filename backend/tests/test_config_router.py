"""
Unit tests for the configuration router (/api/config).

Subject: api/routers/config.py
Scope:   GET and PUT /api/config — config read and (placeholder) update.
Out of scope:
  - Config loading / saving internals     → test_infrastructure_config.py
  - Service initialization                → test_services.py
Setup:   FastAPI TestClient with mocked Services dependency.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import get_services_dep
from api.routers import config as config_router
from infrastructure.config import AppConfig


@pytest.fixture
def mock_services():
    """Return a Services-like object with a realistic AppConfig."""
    services = MagicMock()
    services.config = AppConfig(
        llm_provider="groq",
        chunking={"max_tokens": 512, "overlap_tokens": 128},
    )
    return services


@pytest.fixture
def test_client(mock_services):
    """Build a FastAPI test app with the config router and mocked services."""
    app = FastAPI()
    app.include_router(config_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------


def test_get_config_returns_valid_structure(test_client, mock_services):
    """GET /api/config must return a JSON payload matching the ConfigOut schema."""
    response = test_client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["llm_provider"] == "groq"
    assert "ollama" in body
    assert "openrouter" in body
    assert "huggingface" in body
    assert "chunking" in body
    assert body["chunking"]["max_tokens"] == 512
    assert body["chunking"]["overlap_tokens"] == 128


def test_get_config_includes_ollama_fields(test_client, mock_services):
    """The ollama section must include base_url, generation_model, and timeout."""
    response = test_client.get("/api/config")

    assert response.status_code == 200
    ollama = response.json()["ollama"]
    assert "base_url" in ollama
    assert "generation_model" in ollama
    assert "timeout" in ollama


def test_get_config_ollama_provider(test_client):
    """When the provider is ollama, the response must reflect that choice."""
    services = MagicMock()
    services.config = AppConfig(llm_provider="ollama")

    app = FastAPI()
    app.include_router(config_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: services
    client = TestClient(app)

    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["llm_provider"] == "ollama"


# ---------------------------------------------------------------------------
# PUT /api/config
# ---------------------------------------------------------------------------


def test_put_config_returns_current_config(test_client, mock_services):
    """PUT /api/config (placeholder) must still return the current configuration."""
    response = test_client.put("/api/config", json={"llm_provider": "ollama"})

    assert response.status_code == 200
    body = response.json()
    assert body["llm_provider"] == "groq"
    assert "chunking" in body


def test_put_config_malformed_body_returns_422(test_client):
    """Sending a non-object body where a dict is expected must yield 422."""
    response = test_client.put("/api/config", json="not-a-dict")

    assert response.status_code == 422
