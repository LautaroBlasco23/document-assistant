"""Unit tests for the authentication router (/auth/*)."""
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import infrastructure.auth.jwt_handler as jwt_module
from api.auth import get_current_user
from api.deps import get_services_dep
from api.routers import auth as auth_router
from core.model.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SECRET = "x" * 32


@pytest.fixture(autouse=True)
def _patch_jwt_secret(monkeypatch):
    """Ensure JWT_SECRET is set for every test so token creation works."""
    monkeypatch.setattr(jwt_module, "JWT_SECRET", VALID_SECRET)


@pytest.fixture
def mock_services():
    """Return a Services-like object with mocked user and subscription stores."""
    services = MagicMock()
    services.user_store = MagicMock()
    services.subscription_store = MagicMock()
    return services


@pytest.fixture
def test_client(mock_services):
    """Build a FastAPI test app with dependency overrides for auth routes."""
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api")

    def _services_dep():
        return mock_services

    app.dependency_overrides[get_services_dep] = _services_dep

    # For /auth/me we override get_current_user directly.
    _mock_user = User(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        email="me@example.com",
        password_hash="hash",
        display_name="Me",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    app.dependency_overrides[get_current_user] = lambda: _mock_user

    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

def test_register_success_returns_token(test_client, mock_services):
    """A valid registration must return 201 and an access token."""
    mock_services.user_store.get_by_email.return_value = None
    mock_services.user_store.create.return_value = User(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        email="new@example.com",
        password_hash="hash",
        display_name="New",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    response = test_client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "secret123",
        "display_name": "New",
    })

    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    mock_services.subscription_store.assign_plan.assert_called_once()


def test_register_duplicate_email_returns_400(test_client, mock_services):
    """Registering with an email that already exists must return 400."""
    mock_services.user_store.get_by_email.return_value = MagicMock()

    response = test_client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "secret123",
    })

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_missing_email_returns_422(test_client):
    """Omitting the required email field must trigger Pydantic validation (422)."""
    response = test_client.post("/api/auth/register", json={
        "password": "secret123",
    })

    assert response.status_code == 422


def test_register_missing_password_returns_422(test_client):
    """Omitting the required password field must trigger Pydantic validation (422)."""
    response = test_client.post("/api/auth/register", json={
        "email": "nobody@example.com",
    })

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

def test_login_success_returns_token(test_client, mock_services):
    """A correct email and password must return 200 and a JWT access token."""
    mock_services.user_store.get_by_email.return_value = User(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        email="login@example.com",
        password_hash="hash",
        display_name="Login",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    # Patch verify_password inside the router module because it is imported
    # at module load time; patching the jwt_handler module has no effect.
    with patch("api.routers.auth.verify_password", return_value=True):
        response = test_client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "correct",
        })

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_returns_401(test_client, mock_services):
    """An existing user with a wrong password must receive 401."""
    mock_services.user_store.get_by_email.return_value = User(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        email="login@example.com",
        password_hash="hash",
        display_name="Login",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    with patch("api.routers.auth.verify_password", return_value=False):
        response = test_client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "wrong",
        })

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user_returns_401(test_client, mock_services):
    """A login attempt for an unknown email must receive 401."""
    mock_services.user_store.get_by_email.return_value = None

    response = test_client.post("/api/auth/login", json={
        "email": "ghost@example.com",
        "password": "secret123",
    })

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

def test_me_authenticated_returns_profile(test_client):
    """An authenticated request to /auth/me must return the current user's profile."""
    response = test_client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["display_name"] == "Me"
    assert "id" in body


def test_me_no_token_returns_401(mock_services):
    """A request without an Authorization header must receive 401."""
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    # Do NOT override get_current_user — let the real dependency run.
    client = TestClient(app)

    response = client.get("/api/auth/me")

    assert response.status_code == 401
