"""Unit tests for custom document creation and update API endpoints."""

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_services():
    services = MagicMock()
    services.qdrant.has_file.return_value = False
    services.qdrant.search_by_file.return_value = []
    services.content_store.get_custom_document.return_value = None
    services.task_registry.submit.return_value = "mock-task-id-1234"
    services.config.qdrant.collection_name = "test_collection"
    services.config.ollama.embedding_model = "nomic-embed-text"
    services.config.chunking.max_tokens = 512
    services.config.chunking.overlap_tokens = 128
    return services


@pytest.fixture
def app(mock_services):
    from fastapi import FastAPI
    from api.routers.documents import router
    from api.deps import get_services_dep

    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def override_services():
        return mock_services

    app.dependency_overrides[get_services_dep] = override_services
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /documents/create
# ---------------------------------------------------------------------------


def test_create_document_returns_task_id(client, mock_services):
    payload = {"title": "My Notes", "content": "Some content here.", "document_type": "notes"}
    resp = client.post("/api/documents/create", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert "file_hash" in data
    assert data["title"] == "My Notes"


def test_create_document_hash_matches_content(client, mock_services):
    content = "Unique content for hashing."
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    payload = {"title": "Hash Test", "content": content}
    resp = client.post("/api/documents/create", json=payload)
    assert resp.status_code == 200
    assert resp.json()["file_hash"] == expected_hash


def test_create_duplicate_returns_409(client, mock_services):
    mock_services.qdrant.has_file.return_value = True
    payload = {"title": "Duplicate", "content": "Existing content."}
    resp = client.post("/api/documents/create", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_create_missing_title_returns_422(client):
    resp = client.post("/api/documents/create", json={"content": "Some content"})
    assert resp.status_code == 422


def test_create_empty_title_returns_422(client):
    resp = client.post("/api/documents/create", json={"title": "", "content": "Some content"})
    assert resp.status_code == 422


def test_create_missing_content_returns_422(client):
    resp = client.post("/api/documents/create", json={"title": "Title"})
    assert resp.status_code == 422


def test_create_empty_content_returns_422(client):
    resp = client.post("/api/documents/create", json={"title": "Title", "content": ""})
    assert resp.status_code == 422


def test_create_saves_metadata(client, mock_services):
    payload = {
        "title": "Notes",
        "content": "Content.",
        "description": "My study notes",
        "document_type": "notes",
    }
    resp = client.post("/api/documents/create", json=payload)
    assert resp.status_code == 200
    mock_services.content_store.save_metadata.assert_called_once()
    mock_services.content_store.save_custom_document.assert_called_once()


# ---------------------------------------------------------------------------
# POST /documents/{file_hash}/append
# ---------------------------------------------------------------------------


def test_append_content_to_custom_doc(client, mock_services):
    mock_services.content_store.get_custom_document.return_value = ("My Notes", "Original content.")
    resp = client.post("/api/documents/abc123/append", json={"content": "New chapter content."})
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["file_hash"] == "abc123"


def test_append_to_nonexistent_returns_404(client, mock_services):
    mock_services.content_store.get_custom_document.return_value = None
    resp = client.post("/api/documents/notexist/append", json={"content": "New content."})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_append_empty_content_returns_422(client, mock_services):
    mock_services.content_store.get_custom_document.return_value = ("Title", "Content.")
    resp = client.post("/api/documents/abc123/append", json={"content": ""})
    assert resp.status_code == 422


def test_append_calls_append_custom_document(client, mock_services):
    mock_services.content_store.get_custom_document.return_value = ("Title", "Content.")
    resp = client.post("/api/documents/hash1/append", json={"content": "Appended text."})
    assert resp.status_code == 200
    mock_services.content_store.append_custom_document.assert_called_once_with(
        "hash1", "Appended text."
    )
