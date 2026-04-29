import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

# Configuration
JWT_SECRET = os.getenv("DOCASSIST_AUTH__JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_DAYS = 7
ENCRYPTION_KEY = os.getenv("DOCASSIST_AUTH__ENCRYPTION_KEY")


def validate_jwt_config() -> None:
    """Validate JWT secret is configured. Raises RuntimeError if not."""
    if not JWT_SECRET:
        raise RuntimeError(
            "JWT secret is not configured. "
            "Please set DOCASSIST_AUTH__JWT_SECRET environment variable. "
            "Run 'make jwt-secret' to generate one automatically."
        )

    if len(JWT_SECRET) < 32:
        raise RuntimeError(
            "JWT secret must be at least 32 characters long for security. "
            "Run 'make jwt-secret' to generate a secure secret."
        )


def validate_encryption_config() -> None:
    """Validate encryption key is configured. Raises RuntimeError if not."""
    if not ENCRYPTION_KEY:
        raise RuntimeError(
            "Encryption key is not configured. "
            "Set DOCASSIST_AUTH__ENCRYPTION_KEY environment variable. "
            "Run 'make encryption-key' to generate one."
        )

    if len(ENCRYPTION_KEY) < 32:
        raise RuntimeError(
            "Encryption key must be at least 32 characters long for security. "
            "Run 'make encryption-key' to generate a secure key."
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(user_id: str, email: str) -> str:
    validate_jwt_config()

    expire = datetime.now(timezone.utc) + timedelta(days=JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    validate_jwt_config()

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
