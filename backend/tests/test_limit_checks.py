"""
Unit tests for plan limit enforcement helpers.

Subject: api/limit_checks.py — check_can_create_tree, check_can_create_document
Scope:   HTTP 402 exceptions raised when plan limits are reached.
Out of scope:
  - UserLimits construction logic          → test_user_model.py
  - Subscription store queries             → test_user_repository.py
  - Router integration / auth              → test_users_router.py
Setup:   Pure unit tests — no fixtures or mocks required.
"""

import pytest

from api.limit_checks import PlanLimitExceeded, check_can_create_document, check_can_create_tree
from core.model.user import UserLimits

# ---------------------------------------------------------------------------
# check_can_create_tree
# ---------------------------------------------------------------------------


def test_check_can_create_tree_under_limit_passes():
    """A user with fewer trees than the max should be allowed to create another."""
    limits = UserLimits(
        max_documents=10,
        max_knowledge_trees=5,
        current_documents=2,
        current_knowledge_trees=3,
        can_create_document=True,
        can_create_tree=True,
    )

    # Should not raise
    check_can_create_tree(limits)


def test_check_can_create_tree_at_limit_raises_402():
    """A user who has exactly reached the tree limit must receive 402."""
    limits = UserLimits(
        max_documents=10,
        max_knowledge_trees=5,
        current_documents=2,
        current_knowledge_trees=5,
        can_create_document=True,
        can_create_tree=False,
    )

    with pytest.raises(PlanLimitExceeded) as exc_info:
        check_can_create_tree(limits)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["resource"] == "knowledge_tree"
    assert exc_info.value.detail["current"] == 5
    assert exc_info.value.detail["max"] == 5


def test_check_can_create_tree_over_limit_raises_402():
    """A user who somehow exceeded the tree limit must still receive 402."""
    limits = UserLimits(
        max_documents=10,
        max_knowledge_trees=5,
        current_documents=2,
        current_knowledge_trees=6,
        can_create_document=True,
        can_create_tree=False,
    )

    with pytest.raises(PlanLimitExceeded) as exc_info:
        check_can_create_tree(limits)

    assert exc_info.value.status_code == 402


# ---------------------------------------------------------------------------
# check_can_create_document
# ---------------------------------------------------------------------------


def test_check_can_create_document_under_limit_passes():
    """A user with fewer documents than the max should be allowed to create another."""
    limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=2,
        current_knowledge_trees=1,
        can_create_document=True,
        can_create_tree=True,
    )

    check_can_create_document(limits)


def test_check_can_create_document_at_limit_raises_402():
    """A user who has exactly reached the document limit must receive 402."""
    limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=5,
        current_knowledge_trees=1,
        can_create_document=False,
        can_create_tree=True,
    )

    with pytest.raises(PlanLimitExceeded) as exc_info:
        check_can_create_document(limits)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["resource"] == "document"
    assert exc_info.value.detail["current"] == 5
    assert exc_info.value.detail["max"] == 5


def test_check_can_create_document_over_limit_raises_402():
    """A user who somehow exceeded the document limit must still receive 402."""
    limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=7,
        current_knowledge_trees=1,
        can_create_document=False,
        can_create_tree=True,
    )

    with pytest.raises(PlanLimitExceeded) as exc_info:
        check_can_create_document(limits)

    assert exc_info.value.status_code == 402


# ---------------------------------------------------------------------------
# Plan differentiation
# ---------------------------------------------------------------------------


def test_free_plan_limits_are_low():
    """Free plan limits should be restrictive (3 trees, 5 docs in this fixture)."""
    free_limits = UserLimits(
        max_documents=5,
        max_knowledge_trees=3,
        current_documents=5,
        current_knowledge_trees=3,
        can_create_document=False,
        can_create_tree=False,
    )

    with pytest.raises(PlanLimitExceeded):
        check_can_create_tree(free_limits)

    with pytest.raises(PlanLimitExceeded):
        check_can_create_document(free_limits)


def test_pro_plan_limits_are_high():
    """Pro plan limits should allow many more resources before blocking."""
    pro_limits = UserLimits(
        max_documents=100,
        max_knowledge_trees=50,
        current_documents=42,
        current_knowledge_trees=10,
        can_create_document=True,
        can_create_tree=True,
    )

    # Both should pass without raising
    check_can_create_tree(pro_limits)
    check_can_create_document(pro_limits)
