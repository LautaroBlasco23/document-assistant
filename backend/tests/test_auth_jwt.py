"""Unit tests for JWT token and password utilities."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import jwt as pyjwt

import infrastructure.auth.jwt_handler as jwt_module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SECRET = "a" * 32


def _set_secret(secret: str | None = VALID_SECRET) -> None:
    """Patch the module-level JWT_SECRET for the duration of a test."""
    jwt_module.JWT_SECRET = secret


# ---------------------------------------------------------------------------
# Tests for validate_jwt_config
# ---------------------------------------------------------------------------

def test_validate_jwt_config_raises_when_missing():
    """A missing JWT_SECRET should raise RuntimeError with helpful instructions."""
    _set_secret(None)

    with pytest.raises(RuntimeError, match="JWT secret is not configured"):
        jwt_module.validate_jwt_config()


def test_validate_jwt_config_raises_when_too_short():
    """Secrets shorter than 32 characters are rejected for security."""
    _set_secret("short")

    with pytest.raises(RuntimeError, match="at least 32 characters"):
        jwt_module.validate_jwt_config()


def test_validate_jwt_config_passes_for_valid_secret():
    """A 32+ character secret satisfies the validation without error."""
    _set_secret(VALID_SECRET)

    jwt_module.validate_jwt_config()


# ---------------------------------------------------------------------------
# Tests for get_password_hash
# ---------------------------------------------------------------------------

def test_get_password_hash_produces_non_empty_string():
    """Hashing a password must return a non-empty string."""
    _set_secret(VALID_SECRET)

    hashed = jwt_module.get_password_hash("my_password")

    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_get_password_hash_uses_salt():
    """Two independent calls with the same plaintext must produce different hashes
    because bcrypt salts each call randomly."""
    _set_secret(VALID_SECRET)

    hash_a = jwt_module.get_password_hash("same_password")
    hash_b = jwt_module.get_password_hash("same_password")

    assert hash_a != hash_b


# ---------------------------------------------------------------------------
# Tests for verify_password
# ---------------------------------------------------------------------------

def test_verify_password_matches():
    """verify_password must return True when the plaintext matches the hash."""
    _set_secret(VALID_SECRET)

    hashed = jwt_module.get_password_hash("correct")
    assert jwt_module.verify_password("correct", hashed) is True


def test_verify_password_mismatch():
    """verify_password must return False when the plaintext does not match."""
    _set_secret(VALID_SECRET)

    hashed = jwt_module.get_password_hash("correct")
    assert jwt_module.verify_password("wrong", hashed) is False


# ---------------------------------------------------------------------------
# Tests for create_access_token
# ---------------------------------------------------------------------------

def test_create_access_token_returns_jwt_string():
    """create_access_token must return a non-empty JWT string containing the
    user_id and email in its payload."""
    _set_secret(VALID_SECRET)

    token = jwt_module.create_access_token("user-123", "alice@example.com")

    assert isinstance(token, str)
    assert len(token) > 0

    decoded = pyjwt.decode(token, VALID_SECRET, algorithms=[jwt_module.JWT_ALGORITHM])
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "alice@example.com"
    assert decoded["type"] == "access"


def test_create_access_token_has_default_expiry_in_future():
    """The token must carry an 'exp' claim roughly 7 days from now."""
    _set_secret(VALID_SECRET)

    # JWT timestamps are whole seconds, so truncate microseconds to avoid
    # false negatives when comparing before/after bounds.
    before = datetime.now(timezone.utc).replace(microsecond=0)
    token = jwt_module.create_access_token("user-123", "alice@example.com")
    after = datetime.now(timezone.utc).replace(microsecond=0)

    decoded = pyjwt.decode(token, VALID_SECRET, algorithms=[jwt_module.JWT_ALGORITHM])
    exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

    delta = timedelta(days=jwt_module.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    assert before + delta <= exp <= after + delta + timedelta(minutes=1)


# ---------------------------------------------------------------------------
# Tests for decode_token
# ---------------------------------------------------------------------------

def test_decode_token_returns_payload_for_valid_token():
    """decode_token must return the original payload for an unexpired token."""
    _set_secret(VALID_SECRET)

    token = jwt_module.create_access_token("user-123", "alice@example.com")
    payload = jwt_module.decode_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "alice@example.com"


def test_decode_token_returns_none_for_expired_token():
    """decode_token must return None when the token has expired."""
    _set_secret(VALID_SECRET)

    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "user-123", "email": "alice@example.com", "exp": expire, "type": "access"}
    expired_token = pyjwt.encode(payload, VALID_SECRET, algorithm=jwt_module.JWT_ALGORITHM)

    assert jwt_module.decode_token(expired_token) is None


def test_decode_token_returns_none_for_tampered_token():
    """decode_token must return None when the token signature is invalid."""
    _set_secret(VALID_SECRET)

    token = jwt_module.create_access_token("user-123", "alice@example.com")
    tampered = token[:-5] + "XXXXX"

    assert jwt_module.decode_token(tampered) is None


def test_decode_token_returns_none_for_invalid_secret():
    """decode_token must return None when the token was signed with a different secret."""
    _set_secret(VALID_SECRET)

    token = jwt_module.create_access_token("user-123", "alice@example.com")
    jwt_module.JWT_SECRET = "b" * 32

    assert jwt_module.decode_token(token) is None
