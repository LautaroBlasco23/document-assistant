"""Unit tests for core user domain models."""
from datetime import datetime
from uuid import UUID

from core.model.user import SubscriptionPlan, User, UserLimits, UserSubscription

# ---------------------------------------------------------------------------
# User dataclass
# ---------------------------------------------------------------------------

def test_user_creation():
    """User must store all required fields and expose them as attributes."""
    uid = UUID("12345678-1234-5678-1234-567812345678")
    now = datetime(2024, 6, 1, 12, 0, 0)

    user = User(
        id=uid,
        email="alice@example.com",
        password_hash="hash",
        display_name="Alice",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert user.id == uid
    assert user.email == "alice@example.com"
    assert user.password_hash == "hash"
    assert user.display_name == "Alice"
    assert user.is_active is True
    assert user.created_at == now
    assert user.updated_at == now


def test_user_optional_display_name():
    """display_name may be None for users who did not provide one."""
    user = User(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        email="bob@example.com",
        password_hash="hash",
        display_name=None,
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    assert user.display_name is None


# ---------------------------------------------------------------------------
# SubscriptionPlan dataclass
# ---------------------------------------------------------------------------

def test_subscription_plan_creation():
    """SubscriptionPlan must hold plan metadata and resource limits."""
    plan = SubscriptionPlan(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        slug="pro",
        name="Pro",
        description="Professional tier",
        max_documents=100,
        max_knowledge_trees=50,
        is_active=True,
        created_at=datetime(2024, 1, 1),
    )

    assert plan.slug == "pro"
    assert plan.max_documents == 100
    assert plan.max_knowledge_trees == 50
    assert plan.is_active is True


# ---------------------------------------------------------------------------
# UserSubscription dataclass
# ---------------------------------------------------------------------------

def test_user_subscription_creation():
    """UserSubscription must link a user to a plan with an assignment timestamp."""
    sub = UserSubscription(
        id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        user_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        plan_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        assigned_at=datetime(2024, 3, 1),
    )

    assert sub.user_id == UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    assert sub.plan_id == UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


# ---------------------------------------------------------------------------
# UserLimits — free vs pro plan semantics
# ---------------------------------------------------------------------------

def test_user_limits_free_plan():
    """A UserLimits representing the free plan must have low ceilings."""
    limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=0,
        current_knowledge_trees=0,
        can_create_document=True,
        can_create_tree=True,
    )

    assert limits.max_documents == 5
    assert limits.max_knowledge_trees == 3


def test_user_limits_pro_plan():
    """A UserLimits representing the pro plan must have elevated ceilings."""
    limits = UserLimits(
        max_documents=100,
        max_knowledge_trees=50,
        current_documents=10,
        current_knowledge_trees=5,
        can_create_document=True,
        can_create_tree=True,
    )

    assert limits.max_documents == 100
    assert limits.max_knowledge_trees == 50


def test_user_limits_at_capacity():
    """When usage reaches the plan limit, creation flags must be False."""
    limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=5,
        current_knowledge_trees=3,
        can_create_document=False,
        can_create_tree=False,
    )

    assert limits.can_create_document is False
    assert limits.can_create_tree is False


def test_user_limits_over_capacity():
    """Usage above the limit should also keep creation flags False
    (defensive, even if the application layer prevents this state)."""
    limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=6,
        current_knowledge_trees=4,
        can_create_document=False,
        can_create_tree=False,
    )

    assert limits.can_create_document is False
    assert limits.can_create_tree is False


def test_user_limits_from_plan_mapping():
    """UserLimits fields must correctly reflect the plan that produced them."""
    free_plan = SubscriptionPlan(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        slug="free",
        name="Free",
        description=None,
        max_documents=5,
        max_knowledge_trees=3,
        is_active=True,
        created_at=datetime(2024, 1, 1),
    )

    # Simulate the mapping that the repository layer performs
    limits = UserLimits(
        max_documents=free_plan.max_documents,
        max_knowledge_trees=free_plan.max_knowledge_trees,
        current_documents=2,
        current_knowledge_trees=1,
        can_create_document=2 < free_plan.max_documents,
        can_create_tree=1 < free_plan.max_knowledge_trees,
    )

    assert limits.max_documents == free_plan.max_documents
    assert limits.max_knowledge_trees == free_plan.max_knowledge_trees
    assert limits.can_create_document is True
    assert limits.can_create_tree is True
