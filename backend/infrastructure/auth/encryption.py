"""Symmetric encryption service using Fernet (cryptography package)."""

from cryptography.fernet import Fernet


class EncryptionService:
    """Service for encrypting and decrypting data using Fernet symmetric encryption.

    Uses the ``cryptography.fernet.Fernet`` implementation which provides
    authenticated encryption (AES-128-CBC + HMAC-SHA256).
    """

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, plain: str) -> bytes:
        """Encrypt a plaintext string and return the ciphertext as bytes."""
        return self._fernet.encrypt(plain.encode("utf-8"))

    def decrypt(self, blob: bytes) -> str:
        """Decrypt ciphertext bytes and return the original plaintext string."""
        return self._fernet.decrypt(blob).decode("utf-8")
