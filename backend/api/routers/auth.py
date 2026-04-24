"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.auth import CurrentUser
from api.deps import ServicesDep
from infrastructure.auth.jwt_handler import (
    create_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_days: int = 7


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    created_at: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, services: ServicesDep):
    """Register new user with free plan."""
    existing = services.user_store.get_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = get_password_hash(req.password)
    user = services.user_store.create(
        email=req.email,
        password_hash=password_hash,
        display_name=req.display_name
    )

    # Assign free plan
    services.subscription_store.assign_plan(user.id, "free")

    token = create_access_token(str(user.id), user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, services: ServicesDep):
    """Authenticate and get access token."""
    user = services.user_store.get_by_email(req.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    token = create_access_token(str(user.id), user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: CurrentUser):
    """Get current user profile."""
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        created_at=current_user.created_at.isoformat(),
    )
