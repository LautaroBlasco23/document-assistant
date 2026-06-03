"""Unit tests for the users router (/users/*)."""
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import get_current_user
from api.deps import get_services_dep
from api.routers import users as users_router
from core.model.user import SubscriptionPlan, User, UserLimits

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_user():
    return User(
        id=FIXED_UUID,
        email="user@example.com",
        password_hash="hash",
        display_name="User",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


def _make_plan(slug="free", name="Free", description="Get started"):
    return SubscriptionPlan(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        slug=slug,
        name=name,
        description=description,
        max_documents=200,
        max_knowledge_trees=3,
        is_active=True,
        created_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_limits_free_plan():
    """An authenticated user on the free plan must see low limits, usage, and plan info."""
    mock_services = MagicMock()
    mock_services.subscription_store.get_user_limits.return_value = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=2,
        current_knowledge_trees=1,
        can_create_document=True,
        can_create_tree=True,
    )
    mock_services.subscription_store.get_plan_for_user.return_value = _make_plan()

    app = FastAPI()
    app.include_router(users_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user

    client = TestClient(app)
    response = client.get("/api/users/me/limits")

    assert response.status_code == 200
    body = response.json()
    assert body["max_documents"] == 5
    assert body["max_knowledge_trees"] == 3
    assert body["current_documents"] == 2
    assert body["current_knowledge_trees"] == 1
    assert body["can_create_document"] is True
    assert body["can_create_tree"] is True
    assert body["plan"] == {"slug": "free", "name": "Free", "description": "Get started"}


def test_get_limits_pro_plan():
    """An authenticated user on the pro plan must see elevated limits and pro plan info."""
    mock_services = MagicMock()
    mock_services.subscription_store.get_user_limits.return_value = UserLimits(
        max_documents=100,
        max_knowledge_trees=50,
        current_documents=42,
        current_knowledge_trees=10,
        can_create_document=True,
        can_create_tree=True,
    )
    mock_services.subscription_store.get_plan_for_user.return_value = _make_plan(
        slug="pro", name="Pro", description="For power users"
    )

    app = FastAPI()
    app.include_router(users_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user

    client = TestClient(app)
    response = client.get("/api/users/me/limits")

    assert response.status_code == 200
    body = response.json()
    assert body["max_documents"] == 100
    assert body["max_knowledge_trees"] == 50
    assert body["plan"]["slug"] == "pro"
    assert body["plan"]["name"] == "Pro"


def test_get_limits_at_capacity():
    """When current usage equals the plan limit, creation flags must be False."""
    mock_services = MagicMock()
    mock_services.subscription_store.get_user_limits.return_value = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=5,
        current_knowledge_trees=3,
        can_create_document=False,
        can_create_tree=False,
    )
    mock_services.subscription_store.get_plan_for_user.return_value = _make_plan()

    app = FastAPI()
    app.include_router(users_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user

    client = TestClient(app)
    response = client.get("/api/users/me/limits")

    assert response.status_code == 200
    body = response.json()
    assert body["can_create_document"] is False
    assert body["can_create_tree"] is False


def test_get_limits_no_plan_returns_null():
    """A user with no assigned plan must receive plan: null."""
    mock_services = MagicMock()
    mock_services.subscription_store.get_user_limits.return_value = UserLimits(
        max_documents=0,
        max_knowledge_trees=0,
        current_documents=0,
        current_knowledge_trees=0,
        can_create_document=False,
        can_create_tree=False,
    )
    mock_services.subscription_store.get_plan_for_user.return_value = None

    app = FastAPI()
    app.include_router(users_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user

    client = TestClient(app)
    response = client.get("/api/users/me/limits")

    assert response.status_code == 200
    assert response.json()["plan"] is None


def test_get_limits_no_token_returns_401():
    """A request without authentication must receive 401."""
    mock_services = MagicMock()

    app = FastAPI()
    app.include_router(users_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    # Do not override get_current_user — real dependency requires a Bearer token.

    client = TestClient(app)
    response = client.get("/api/users/me/limits")

    assert response.status_code == 401
