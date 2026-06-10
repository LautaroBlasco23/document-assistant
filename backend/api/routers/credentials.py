"""Credentials management endpoints — per-user encrypted LLM API keys."""

import logging

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep
from application.services.provider_service import test_provider

logger = logging.getLogger(__name__)

router = APIRouter()

_KNOWN_PROVIDERS = frozenset({"groq", "openrouter", "huggingface", "nvidia", "gemini", "ollama", "llamacpp"})
_ALL_PROVIDERS = ["groq", "openrouter", "huggingface", "nvidia", "gemini", "ollama", "llamacpp"]


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class SaveCredentialRequest(BaseModel):
    api_key: str


class TestCredentialRequest(BaseModel):
    api_key: str | None = None  # if None, use stored key


class CredentialStatusOut(BaseModel):
    provider: str
    configured: bool
    last4: str | None
    last_tested_at: str | None  # ISO format
    last_test_ok: bool | None
    last_test_error: str | None


class TestConnectionResult(BaseModel):
    ok: bool
    error: str | None = None
    model_count: int | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/credentials", response_model=list[CredentialStatusOut])
async def list_credentials(
    current_user: CurrentUser, services: ServicesDep,
) -> list[CredentialStatusOut]:
    """List per-user provider credential status (one entry per known provider)."""
    stored = services.llm_credential_store.list_for_user(current_user.id)
    stored_by_provider = {c.provider: c for c in stored}

    results: list[CredentialStatusOut] = []
    for provider in _ALL_PROVIDERS:
        cred = stored_by_provider.get(provider)
        if cred is not None:
            results.append(
                CredentialStatusOut(
                    provider=provider,
                    configured=True,
                    last4=cred.api_key_last4,
                    last_tested_at=cred.last_tested_at.isoformat() if cred.last_tested_at else None,
                    last_test_ok=cred.last_test_ok,
                    last_test_error=cred.last_test_error,
                )
            )
        else:
            results.append(
                CredentialStatusOut(
                    provider=provider,
                    configured=False,
                    last4=None,
                    last_tested_at=None,
                    last_test_ok=None,
                    last_test_error=None,
                )
            )
    return results


@router.put("/credentials/{provider}", response_model=CredentialStatusOut)
async def save_credential(
    provider: str,
    req: SaveCredentialRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> CredentialStatusOut:
    """Encrypt and store an API key for a provider, then auto-test the connection."""
    if provider not in _KNOWN_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {provider}")
    if provider == "ollama":
        raise HTTPException(status_code=400, detail="Ollama does not use API keys")
    if provider == "llamacpp":
        raise HTTPException(status_code=400, detail="llama.cpp does not use API keys")

    encrypted = services.encryption.encrypt(req.api_key)
    last4 = req.api_key[-4:] if len(req.api_key) >= 4 else ""
    cred = services.llm_credential_store.upsert(current_user.id, provider, encrypted, last4)

    # Auto-test on save
    ok, error, _ = test_provider(provider, req.api_key, services.config)
    services.llm_credential_store.update_test_result(current_user.id, provider, ok, error)
    # Refresh to get updated timestamps
    cred = services.llm_credential_store.get(current_user.id, provider) or cred

    return CredentialStatusOut(
        provider=provider,
        configured=True,
        last4=cred.api_key_last4,
        last_tested_at=cred.last_tested_at.isoformat() if cred.last_tested_at else None,
        last_test_ok=cred.last_test_ok,
        last_test_error=cred.last_test_error,
    )


@router.delete("/credentials/{provider}", status_code=204)
async def delete_credential(
    provider: str,
    current_user: CurrentUser,
    services: ServicesDep,
) -> Response:
    """Delete a stored provider credential."""
    if provider not in _KNOWN_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {provider}")
    services.llm_credential_store.delete(current_user.id, provider)
    return Response(status_code=204)


@router.post("/credentials/{provider}/test", response_model=TestConnectionResult)
async def test_credential(
    provider: str,
    req: TestCredentialRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> TestConnectionResult:
    """Test a provider connection using the supplied or stored API key."""
    if provider not in _KNOWN_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {provider}")

    if req.api_key is not None:
        api_key = req.api_key
    else:
        encrypted = services.llm_credential_store.get_encrypted_key(current_user.id, provider)
        if encrypted is None:
            raise HTTPException(status_code=404, detail="No credential stored for this provider")
        api_key = services.encryption.decrypt(encrypted)

    ok, error, model_count = test_provider(provider, api_key, services.config)
    services.llm_credential_store.update_test_result(current_user.id, provider, ok, error)

    return TestConnectionResult(ok=ok, error=error, model_count=model_count)
