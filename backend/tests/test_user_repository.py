"""Unit tests for PostgreSQL user and subscription repositories."""
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from core.model.user import SubscriptionPlan, User, UserLimits, UserSubscription
from infrastructure.db.user_repository import (
    PostgresSubscriptionPlanStore,
    PostgresUserStore,
    PostgresUserSubscriptionStore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")


def _make_pool_and_cursor():
    """Return a mocked PostgresPool and cursor that records executed SQL."""
    pool = MagicMock()
    cur = MagicMock()
    conn = MagicMock()

    # psycopg dict_row cursor returns dict-like rows
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []

    # cursor context manager
    cm_cur = MagicMock()
    cm_cur.__enter__ = MagicMock(return_value=cur)
    cm_cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cm_cur

    # transaction context manager (no-op)
    cm_tx = MagicMock()
    cm_tx.__enter__ = MagicMock(return_value=None)
    cm_tx.__exit__ = MagicMock(return_value=False)
    conn.transaction.return_value = cm_tx

    # connection info
    conn.info.transaction_status = 0  # IDLE

    # pool returns the same connection
    pool.connection.return_value = conn

    return pool, cur, conn


def _user_row(
    user_id=FIXED_UUID,
    email="alice@example.com",
    password_hash="hash",
    display_name="Alice",
    is_active=True,
    created_at=None,
    updated_at=None,
):
    return {
        "id": user_id,
        "email": email,
        "password_hash": password_hash,
        "display_name": display_name,
        "is_active": is_active,
        "created_at": created_at or datetime(2024, 1, 1),
        "updated_at": updated_at or datetime(2024, 1, 1),
    }


def _plan_row(
    plan_id=FIXED_UUID,
    slug="free",
    name="Free",
    description=None,
    max_documents=5,
    max_knowledge_trees=3,
    is_active=True,
    created_at=None,
):
    return {
        "id": plan_id,
        "slug": slug,
        "name": name,
        "description": description,
        "max_documents": max_documents,
        "max_knowledge_trees": max_knowledge_trees,
        "is_active": is_active,
        "created_at": created_at or datetime(2024, 1, 1),
    }


def _subscription_row(
    sub_id=FIXED_UUID,
    user_id=FIXED_UUID,
    plan_id=FIXED_UUID,
    assigned_at=None,
):
    return {
        "id": sub_id,
        "user_id": user_id,
        "plan_id": plan_id,
        "assigned_at": assigned_at or datetime(2024, 1, 1),
    }


# ---------------------------------------------------------------------------
# PostgresUserStore
# ---------------------------------------------------------------------------

def test_user_store_create_returns_user():
    """create must insert a row and return a fully populated User object."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _user_row()

    store = PostgresUserStore(pool)
    user = store.create("alice@example.com", "hash", "Alice")

    assert isinstance(user, User)
    assert user.email == "alice@example.com"
    assert user.password_hash == "hash"
    assert user.display_name == "Alice"
    assert user.is_active is True


def test_user_store_get_by_email_found():
    """get_by_email must return the User when a matching row exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _user_row(email="bob@example.com")

    store = PostgresUserStore(pool)
    user = store.get_by_email("bob@example.com")

    assert user is not None
    assert user.email == "bob@example.com"


def test_user_store_get_by_email_not_found():
    """get_by_email must return None when no row matches."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresUserStore(pool)
    user = store.get_by_email("nobody@example.com")

    assert user is None


def test_user_store_get_by_id_found():
    """get_by_id must return the User when a matching row exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _user_row(user_id=FIXED_UUID)

    store = PostgresUserStore(pool)
    user = store.get_by_id(FIXED_UUID)

    assert user is not None
    assert user.id == FIXED_UUID


def test_user_store_get_by_id_not_found():
    """get_by_id must return None when the UUID does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresUserStore(pool)
    user = store.get_by_id(FIXED_UUID)

    assert user is None


def test_user_store_duplicate_email_raises():
    """create must propagate a database error when the email violates a unique constraint."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.execute.side_effect = Exception("duplicate key value violates unique constraint")

    store = PostgresUserStore(pool)
    with pytest.raises(Exception, match="duplicate key value"):
        store.create("alice@example.com", "hash", "Alice")


# ---------------------------------------------------------------------------
# PostgresSubscriptionPlanStore
# ---------------------------------------------------------------------------

def test_plan_store_get_by_slug_found():
    """get_by_slug must return the SubscriptionPlan for an existing slug."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _plan_row(slug="pro")

    store = PostgresSubscriptionPlanStore(pool)
    plan = store.get_by_slug("pro")

    assert isinstance(plan, SubscriptionPlan)
    assert plan.slug == "pro"


def test_plan_store_get_by_slug_not_found():
    """get_by_slug must return None when the slug does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresSubscriptionPlanStore(pool)
    plan = store.get_by_slug("enterprise")

    assert plan is None


def test_plan_store_list_active_returns_plans():
    """list_active must return all active plans ordered by created_at."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _plan_row(slug="free", max_documents=5),
        _plan_row(slug="pro", max_documents=100),
    ]

    store = PostgresSubscriptionPlanStore(pool)
    plans = store.list_active()

    assert len(plans) == 2
    assert plans[0].slug == "free"
    assert plans[1].slug == "pro"
    assert plans[1].max_documents == 100


def test_plan_store_list_active_empty():
    """list_active must return an empty list when no active plans exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = []

    store = PostgresSubscriptionPlanStore(pool)
    plans = store.list_active()

    assert plans == []


# ---------------------------------------------------------------------------
# PostgresUserSubscriptionStore
# ---------------------------------------------------------------------------

def test_subscription_store_assign_plan_creates_subscription():
    """assign_plan must delete any existing subscription and insert a new one."""
    pool, cur, _ = _make_pool_and_cursor()
    # First call: plan lookup
    # Second call: DELETE existing
    # Third call: INSERT new (fetchone)
    cur.fetchone.side_effect = [
        _plan_row(slug="free"),  # plan lookup
        _subscription_row(),       # INSERT returning
    ]

    store = PostgresUserSubscriptionStore(pool)
    sub = store.assign_plan(FIXED_UUID, "free")

    assert isinstance(sub, UserSubscription)
    assert sub.user_id == FIXED_UUID
    assert cur.execute.call_count == 3


def test_subscription_store_assign_plan_raises_for_unknown_slug():
    """assign_plan must raise ValueError when the plan slug does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None  # plan not found

    store = PostgresUserSubscriptionStore(pool)
    with pytest.raises(ValueError, match="Plan not found: premium"):
        store.assign_plan(FIXED_UUID, "premium")


def test_subscription_store_get_for_user_found():
    """get_for_user must return the UserSubscription when one exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _subscription_row()

    store = PostgresUserSubscriptionStore(pool)
    sub = store.get_for_user(FIXED_UUID)

    assert isinstance(sub, UserSubscription)
    assert sub.user_id == FIXED_UUID


def test_subscription_store_get_for_user_not_found():
    """get_for_user must return None when the user has no subscription."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresUserSubscriptionStore(pool)
    sub = store.get_for_user(FIXED_UUID)

    assert sub is None


def test_subscription_store_get_user_limits_with_plan():
    """get_user_limits must compute can_create flags from plan limits and
    current usage counts."""
    pool, cur, _ = _make_pool_and_cursor()

    # Plan lookup for get_plan_for_user
    # Document count
    # Tree count
    cur.fetchone.side_effect = [
        _plan_row(max_documents=10, max_knowledge_trees=5),
        {"count": 3},
        {"count": 5},
    ]

    store = PostgresUserSubscriptionStore(pool)
    limits = store.get_user_limits(FIXED_UUID)

    assert isinstance(limits, UserLimits)
    assert limits.max_documents == 10
    assert limits.max_knowledge_trees == 5
    assert limits.current_documents == 3
    assert limits.current_knowledge_trees == 5
    assert limits.can_create_document is True   # 3 < 10
    assert limits.can_create_tree is False      # 5 < 5 is False


def test_subscription_store_get_user_limits_without_plan():
    """get_user_limits must return zeroed-out limits when the user has no plan."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None  # no plan

    store = PostgresUserSubscriptionStore(pool)
    limits = store.get_user_limits(FIXED_UUID)

    assert limits.max_documents == 0
    assert limits.max_knowledge_trees == 0
    assert limits.current_documents == 0
    assert limits.current_knowledge_trees == 0
    assert limits.can_create_document is False
    assert limits.can_create_tree is False
