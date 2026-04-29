"""Unit tests for EncryptionService."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from infrastructure.auth.encryption import EncryptionService


def _make_service() -> EncryptionService:
    return EncryptionService(Fernet.generate_key())


def test_round_trip():
    svc = _make_service()
    assert svc.decrypt(svc.encrypt("hello world")) == "hello world"


def test_empty_string():
    svc = _make_service()
    assert svc.decrypt(svc.encrypt("")) == ""


def test_unicode():
    svc = _make_service()
    value = "gsk_日本語テスト"
    assert svc.decrypt(svc.encrypt(value)) == value


def test_wrong_key_raises():
    svc_a = _make_service()
    svc_b = _make_service()
    blob = svc_a.encrypt("secret")
    with pytest.raises(InvalidToken):
        svc_b.decrypt(blob)


def test_short_key_raises():
    with pytest.raises(Exception):
        EncryptionService(b"tooshort")
