import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

# Configuration
JWT_SECRET = os.getenv("DOCASSIST_AUTH__JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


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
