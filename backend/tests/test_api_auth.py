"""Unit tests for FastAPI authentication dependency get_current_user."""
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.auth import get_current_user
from core.model.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _make_user(**kwargs):
    defaults = {
        "id": FIXED_UUID,
        "email": "test@example.com",
        "password_hash": "hash",
        "display_name": "Test",
        "is_active": True,
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 1),
    }
    defaults.update(kwargs)
    return User(**defaults)


def _run(coro):
    """Run an async coroutine in a sync test."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_current_user_valid_token_returns_user():
    """A valid Bearer token that maps to an active user must return that User."""
    mock_services = MagicMock()
    mock_services.user_store.get_by_id.return_value = _make_user()

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    with patch("api.auth.decode_token", return_value={"sub": str(FIXED_UUID)}):
        user = _run(get_current_user(credentials=creds, services=mock_services))

    assert user is not None
    assert user.id == FIXED_UUID
    assert user.email == "test@example.com"


def test_get_current_user_missing_header_raises_401():
    """When no Authorization header is present get_current_user must raise 401."""
    mock_services = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        _run(get_current_user(credentials=None, services=mock_services))

    assert exc_info.value.status_code == 401
    assert "Authorization header required" in exc_info.value.detail


def test_get_current_user_invalid_token_raises_401():
    """A token that fails signature or format validation must raise 401."""
    mock_services = MagicMock()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")

    with patch("api.auth.decode_token", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(credentials=creds, services=mock_services))

    assert exc_info.value.status_code == 401
    assert "Invalid or expired token" in exc_info.value.detail


def test_get_current_user_expired_token_raises_401():
    """An expired token (decode_token returns None) must raise 401."""
    mock_services = MagicMock()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired_token")

    with patch("api.auth.decode_token", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(credentials=creds, services=mock_services))

    assert exc_info.value.status_code == 401


def test_get_current_user_missing_sub_raises_401():
    """A token payload without a 'sub' claim must raise 401."""
    mock_services = MagicMock()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="no_sub_token")

    with patch("api.auth.decode_token", return_value={"email": "test@example.com"}):
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(credentials=creds, services=mock_services))

    assert exc_info.value.status_code == 401
    assert "Invalid token payload" in exc_info.value.detail


def test_get_current_user_user_not_found_raises_401():
    """A valid token for a deleted/nonexistent user must raise 401."""
    mock_services = MagicMock()
    mock_services.user_store.get_by_id.return_value = None
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    with patch("api.auth.decode_token", return_value={"sub": str(FIXED_UUID)}):
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(credentials=creds, services=mock_services))

    assert exc_info.value.status_code == 401
    assert "User not found" in exc_info.value.detail


def test_get_current_user_inactive_account_raises_403():
    """A valid token for a deactivated user must raise 403."""
    mock_services = MagicMock()
    mock_services.user_store.get_by_id.return_value = _make_user(is_active=False)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

    with patch("api.auth.decode_token", return_value={"sub": str(FIXED_UUID)}):
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(credentials=creds, services=mock_services))

    assert exc_info.value.status_code == 403
    assert "Account deactivated" in exc_info.value.detail
