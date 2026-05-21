"""
Unit tests for the credentials router (/api/credentials).

Subject: api/routers/credentials.py
Scope:   GET/PUT/DELETE /credentials and POST /credentials/{provider}/test
Out of scope:
  - Actual provider API calls               → integration tests
  - Encryption internals                    → test_encryption.py
Setup:   FastAPI TestClient with mocked services and current user.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import get_current_user
from api.deps import get_services_dep
from api.routers import credentials as credentials_router
from core.model.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _make_user():
    return User(
        id=USER_ID,
        email="user@example.com",
        password_hash="hash",
        display_name="User",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_services():
    svc = MagicMock()
    svc.config = MagicMock()
    svc.encryption = MagicMock()
    svc.llm_credential_store = MagicMock()
    return svc


@pytest.fixture
def test_client(mock_services):
    app = FastAPI()
    app.include_router(credentials_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user
    return TestClient(app)


def _make_credential(provider: str, last4: str = "key1") -> MagicMock:
    cred = MagicMock()
    cred.provider = provider
    cred.api_key_last4 = last4
    cred.last_tested_at = datetime(2024, 6, 1)
    cred.last_test_ok = True
    cred.last_test_error = None
    return cred


# ---------------------------------------------------------------------------
# GET /api/credentials
# ---------------------------------------------------------------------------


def test_list_credentials_returns_all_providers(test_client, mock_services):
    """list_credentials must return one entry per known provider."""
    mock_services.llm_credential_store.list_for_user.return_value = []
    response = test_client.get("/api/credentials")
    assert response.status_code == 200
    body = response.json()
    providers = {item["provider"] for item in body}
    assert "groq" in providers
    assert "openrouter" in providers
    assert "ollama" in providers


def test_list_credentials_configured_provider_shows_details(test_client, mock_services):
    """A stored credential must appear as configured=True with the last4 visible."""
    groq_cred = _make_credential("groq", last4="k123")
    mock_services.llm_credential_store.list_for_user.return_value = [groq_cred]

    response = test_client.get("/api/credentials")
    body = response.json()
    groq_entry = next(item for item in body if item["provider"] == "groq")
    assert groq_entry["configured"] is True
    assert groq_entry["last4"] == "k123"
    assert groq_entry["last_test_ok"] is True


def test_list_credentials_unconfigured_provider_shows_false(test_client, mock_services):
    """Providers without a stored credential must appear as configured=False."""
    mock_services.llm_credential_store.list_for_user.return_value = []
    response = test_client.get("/api/credentials")
    body = response.json()
    for item in body:
        assert item["configured"] is False
        assert item["last4"] is None


# ---------------------------------------------------------------------------
# PUT /api/credentials/{provider}
# ---------------------------------------------------------------------------


def test_save_credential_encrypts_and_stores(test_client, mock_services):
    """PUT must encrypt the key, store it, and return a CredentialStatusOut."""
    mock_services.encryption.encrypt.return_value = b"encrypted-bytes"
    cred = _make_credential("groq", last4="abc1")
    mock_services.llm_credential_store.upsert.return_value = cred
    mock_services.llm_credential_store.get.return_value = cred

    with patch("api.routers.credentials.test_provider", return_value=(True, None, 10)):
        response = test_client.put("/api/credentials/groq", json={"api_key": "gsk_abc12345"})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "groq"
    assert body["configured"] is True
    mock_services.encryption.encrypt.assert_called_once_with("gsk_abc12345")
    mock_services.llm_credential_store.upsert.assert_called_once()


def test_save_credential_last4_computed_correctly(test_client, mock_services):
    """last4 must be the final 4 chars of the raw api_key, not the encrypted blob."""
    cred = _make_credential("groq", last4="4321")
    mock_services.llm_credential_store.upsert.return_value = cred
    mock_services.llm_credential_store.get.return_value = cred

    with patch("api.routers.credentials.test_provider", return_value=(True, None, 5)):
        test_client.put("/api/credentials/groq", json={"api_key": "prefix_4321"})

    upsert_args = mock_services.llm_credential_store.upsert.call_args.args
    assert upsert_args[3] == "4321"


def test_save_credential_unknown_provider_returns_422(test_client, mock_services):
    """PUT to an unknown provider must return 422."""
    response = test_client.put("/api/credentials/fakeai", json={"api_key": "key"})
    assert response.status_code == 422
    assert "Unknown provider" in response.json()["detail"]


def test_save_credential_ollama_returns_400(test_client, mock_services):
    """PUT to ollama must return 400 because Ollama needs no API key."""
    response = test_client.put("/api/credentials/ollama", json={"api_key": "key"})
    assert response.status_code == 400
    assert "ollama" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/credentials/{provider}
# ---------------------------------------------------------------------------


def test_delete_credential_calls_store(test_client, mock_services):
    """DELETE must call llm_credential_store.delete and return 204."""
    response = test_client.delete("/api/credentials/groq")
    assert response.status_code == 204
    mock_services.llm_credential_store.delete.assert_called_once_with(USER_ID, "groq")


def test_delete_credential_unknown_provider_returns_422(test_client, mock_services):
    """DELETE to an unknown provider must return 422."""
    response = test_client.delete("/api/credentials/unknown")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/credentials/{provider}/test
# ---------------------------------------------------------------------------


def test_test_credential_with_inline_key(test_client, mock_services):
    """POST with api_key in body must use that key directly."""
    with patch(
        "api.routers.credentials.test_provider", return_value=(True, None, 42)
    ) as mock_test:
        response = test_client.post(
            "/api/credentials/groq/test", json={"api_key": "gsk_inline_key"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["model_count"] == 42
    mock_test.assert_called_once()
    assert mock_test.call_args.args[1] == "gsk_inline_key"


def test_test_credential_with_stored_key(test_client, mock_services):
    """POST without api_key must decrypt and use the stored key."""
    mock_services.llm_credential_store.get_encrypted_key.return_value = b"encrypted-blob"
    mock_services.encryption.decrypt.return_value = "gsk_stored_key"

    with patch(
        "api.routers.credentials.test_provider", return_value=(False, "bad key", None)
    ) as mock_test:
        response = test_client.post("/api/credentials/groq/test", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "bad key"
    mock_services.encryption.decrypt.assert_called_once_with(b"encrypted-blob")
    assert mock_test.call_args.args[1] == "gsk_stored_key"


def test_test_credential_no_stored_key_returns_404(test_client, mock_services):
    """POST without api_key when no credential is stored must return 404."""
    mock_services.llm_credential_store.get_encrypted_key.return_value = None
    response = test_client.post("/api/credentials/groq/test", json={})
    assert response.status_code == 404
    assert "No credential" in response.json()["detail"]


def test_test_credential_unknown_provider_returns_422(test_client, mock_services):
    """POST to an unknown provider must return 422."""
    response = test_client.post("/api/credentials/badprovider/test", json={"api_key": "x"})
    assert response.status_code == 422


def test_test_credential_updates_test_result(test_client, mock_services):
    """After testing, update_test_result must be called to persist the outcome."""
    with patch("api.routers.credentials.test_provider", return_value=(True, None, 5)):
        test_client.post("/api/credentials/groq/test", json={"api_key": "key"})

    mock_services.llm_credential_store.update_test_result.assert_called_once_with(
        USER_ID, "groq", True, None
    )


def test_test_provider_huggingface_always_ok(test_client, mock_services):
    """HuggingFace has no model-listing API; save must treat it as ok."""
    cred = _make_credential("huggingface", last4="fxyz")
    mock_services.llm_credential_store.upsert.return_value = cred
    mock_services.llm_credential_store.get.return_value = cred

    response = test_client.put("/api/credentials/huggingface", json={"api_key": "hf_key_fxyz"})
    assert response.status_code == 200
    assert response.json()["configured"] is True
