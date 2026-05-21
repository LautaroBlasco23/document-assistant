"""
Unit tests for the encryption config validation.

Subject: infrastructure/auth/jwt_handler.py — validate_encryption_config()
Scope:   Encryption key validation (missing, too short, valid).
Out of scope:
  - JWT token operations             → test_auth_jwt.py
  - Password hashing                 → test_auth_jwt.py
  - EncryptionService                → test_encryption.py
Setup:   Module-level ENCRYPTION_KEY is patched directly.
"""

import pytest

import infrastructure.auth.jwt_handler as jwt_module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_KEY = "a" * 32


def _set_key(key: str | None = VALID_KEY) -> None:
    """Patch the module-level ENCRYPTION_KEY for the duration of a test."""
    jwt_module.ENCRYPTION_KEY = key


# ---------------------------------------------------------------------------
# Tests for validate_encryption_config
# ---------------------------------------------------------------------------


def test_validate_encryption_config_raises_when_missing():
    """A missing ENCRYPTION_KEY should raise RuntimeError with helpful instructions."""
    _set_key(None)

    with pytest.raises(RuntimeError, match="Encryption key is not configured"):
        jwt_module.validate_encryption_config()


def test_validate_encryption_config_raises_when_too_short():
    """Keys shorter than 32 characters are rejected for security."""
    _set_key("short")

    with pytest.raises(RuntimeError, match="at least 32 characters"):
        jwt_module.validate_encryption_config()


def test_validate_encryption_config_passes_for_valid_key():
    """A 32+ character key satisfies the validation without error."""
    _set_key(VALID_KEY)

    jwt_module.validate_encryption_config()


def test_validate_encryption_config_passes_for_longer_key():
    """Keys longer than 32 characters are accepted."""
    _set_key("b" * 64)

    jwt_module.validate_encryption_config()
