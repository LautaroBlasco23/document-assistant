"""FastAPI authentication dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.deps import ServicesDep
from core.model.user import User
from infrastructure.auth.jwt_handler import decode_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = Query(None),
    services: ServicesDep = None,
) -> User:
    """
    Extract and validate JWT from Authorization header or ?token= query param.
    Query-param fallback is needed for endpoints serving files to <embed>/<Document>
    tags that cannot set custom headers (PDF viewer, thumbnails).
    Returns authenticated User or raises 401/403.
    """
    raw_token: str | None = None
    if credentials is not None:
        raw_token = credentials.credentials
    elif token is not None:
        raw_token = token

    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header or ?token= query param required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(raw_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from uuid import UUID
    user = services.user_store.get_by_id(UUID(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
