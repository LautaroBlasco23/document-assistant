"""
Integration tests for the DB repository layer (users, subscriptions, tasks).

Requires a running PostgreSQL instance (docker compose up -d).
Run with:  uv run pytest -m integration

Infrastructure: Local PostgreSQL via docker-compose, schema applied on connect.
Data strategy: Explicit cleanup via raw SQL DELETE in finally blocks.
Parallel-safe: no — tests share a module-scoped connection and run sequentially.
"""

from uuid import uuid4

import pytest

from core.model.user import User
from infrastructure.config import AppConfig
from infrastructure.db.postgres import PostgresPool
from infrastructure.db.task_repository import TaskRepository
from infrastructure.db.user_repository import (
    PostgresSubscriptionPlanStore,
    PostgresUserStore,
    PostgresUserSubscriptionStore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pool():
    """Connect to the local PostgreSQL instance and apply schema/migrations."""
    cfg = AppConfig().postgres
    p = PostgresPool(cfg)
    try:
        p.connect()
    except Exception:
        pytest.skip("PostgreSQL not reachable — skipping integration tests")
    yield p
    p.close()


@pytest.fixture(scope="module")
def user_store(pool):
    return PostgresUserStore(pool)


@pytest.fixture(scope="module")
def plan_store(pool):
    return PostgresSubscriptionPlanStore(pool)


@pytest.fixture(scope="module")
def subscription_store(pool):
    return PostgresUserSubscriptionStore(pool)


@pytest.fixture(scope="module")
def task_repo(pool):
    return TaskRepository(pool)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _delete_user(pool, user_id):
    conn = pool.connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()


def _delete_task(pool, task_id):
    conn = pool.connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM background_tasks WHERE task_id = %s", (task_id,))
    conn.commit()


def _get_task_raw(pool, task_id):
    conn = pool.connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT task_id, task_type, status, progress, progress_pct, result, error, "
            "doc_hash, filename, chapter, book_title "
            "FROM background_tasks WHERE task_id = %s",
            (task_id,),
        )
        return cur.fetchone()


def _insert_plan(pool, slug, name, max_documents=10, max_knowledge_trees=5):
    conn = pool.connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO subscription_plans (slug, name, max_documents, max_knowledge_trees) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id",
            (slug, name, max_documents, max_knowledge_trees),
        )
        row = cur.fetchone()
    conn.commit()
    return row["id"]


# ---------------------------------------------------------------------------
# PostgresUserStore
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_user_store_create_and_get_by_email(user_store, pool):
    """Creating a user must persist it so get_by_email can retrieve it."""
    email = f"create-get-{uuid4()}@example.com"
    user = user_store.create(email, "hashed_password", "Test User")
    try:
        assert isinstance(user, User)
        assert user.email == email
        assert user.password_hash == "hashed_password"
        assert user.display_name == "Test User"
        assert user.is_active is True

        fetched = user_store.get_by_email(email)
        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.email == email
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_user_store_get_by_id(user_store, pool):
    """get_by_id must return the correct user for an existing UUID."""
    email = f"get-by-id-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        fetched = user_store.get_by_id(user.id)
        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.email == email
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_user_store_get_by_id_not_found(user_store):
    """get_by_id must return None for a random UUID."""
    result = user_store.get_by_id(uuid4())
    assert result is None


@pytest.mark.integration
def test_user_store_duplicate_email_raises(user_store, pool):
    """Creating a user with a duplicate email must raise a database error."""
    email = f"dup-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        with pytest.raises(Exception, match="unique constraint"):
            user_store.create(email, "other_hash", "Other")
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_user_store_update_user(user_store, pool):
    """update must modify display_name and is_active fields."""
    email = f"update-{uuid4()}@example.com"
    user = user_store.create(email, "hash", "Original")
    try:
        user.display_name = "Updated"
        user.is_active = False
        updated = user_store.update(user)
        assert updated.display_name == "Updated"
        assert updated.is_active is False

        fetched = user_store.get_by_id(user.id)
        assert fetched.display_name == "Updated"
        assert fetched.is_active is False
    finally:
        _delete_user(pool, user.id)


# ---------------------------------------------------------------------------
# PostgresSubscriptionPlanStore
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_plan_store_get_by_slug_found(plan_store):
    """get_by_slug must return the pre-seeded 'free' plan."""
    plan = plan_store.get_by_slug("free")
    assert plan is not None
    assert plan.slug == "free"
    assert plan.name == "Free"
    assert plan.max_documents == 200
    assert plan.max_knowledge_trees == 3


@pytest.mark.integration
def test_plan_store_list_active(plan_store):
    """list_active must include at least the pre-seeded 'free' plan."""
    plans = plan_store.list_active()
    slugs = {p.slug for p in plans}
    assert "free" in slugs


# ---------------------------------------------------------------------------
# PostgresUserSubscriptionStore
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_subscription_store_assign_plan(subscription_store, user_store, pool):
    """assign_plan must link a user to an existing plan."""
    email = f"sub-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        sub = subscription_store.assign_plan(user.id, "free")
        assert sub.user_id == user.id
        assert sub.plan_id is not None
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_subscription_store_get_for_user(subscription_store, user_store, pool):
    """get_for_user must return the active subscription for a user."""
    email = f"sub-get-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        subscription_store.assign_plan(user.id, "free")
        sub = subscription_store.get_for_user(user.id)
        assert sub is not None
        assert sub.user_id == user.id
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_subscription_store_get_plan_for_user(subscription_store, user_store, pool):
    """get_plan_for_user must return the plan details linked to a user."""
    email = f"sub-plan-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        subscription_store.assign_plan(user.id, "free")
        plan = subscription_store.get_plan_for_user(user.id)
        assert plan is not None
        assert plan.slug == "free"
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_subscription_store_upgrade_plan(subscription_store, user_store, pool):
    """assign_plan called twice must replace the previous subscription (upgrade)."""
    email = f"sub-upg-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        pro_id = _insert_plan(pool, "pro-test", "Pro Test", 1000, 10)

        sub_free = subscription_store.assign_plan(user.id, "free")
        assert sub_free.plan_id is not None

        sub_pro = subscription_store.assign_plan(user.id, "pro-test")
        assert sub_pro.plan_id == pro_id

        current = subscription_store.get_for_user(user.id)
        assert current.plan_id == pro_id
    finally:
        _delete_user(pool, user.id)
        conn = pool.connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM subscription_plans WHERE slug = %s", ("pro-test",))
        conn.commit()


@pytest.mark.integration
def test_subscription_store_get_user_limits(subscription_store, user_store, pool):
    """get_user_limits must reflect the plan limits and current usage (zero)."""
    email = f"sub-lim-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        subscription_store.assign_plan(user.id, "free")
        limits = subscription_store.get_user_limits(user.id)
        assert limits.max_documents == 200
        assert limits.max_knowledge_trees == 3
        assert limits.current_documents == 0
        assert limits.current_knowledge_trees == 0
        assert limits.can_create_document is True
        assert limits.can_create_tree is True
    finally:
        _delete_user(pool, user.id)


@pytest.mark.integration
def test_subscription_store_assign_unknown_plan_raises(subscription_store, user_store, pool):
    """assign_plan must raise ValueError when the plan slug does not exist."""
    email = f"sub-unk-{uuid4()}@example.com"
    user = user_store.create(email, "hash", None)
    try:
        with pytest.raises(ValueError, match="Plan not found"):
            subscription_store.assign_plan(user.id, "nonexistent-plan-12345")
    finally:
        _delete_user(pool, user.id)


# ---------------------------------------------------------------------------
# TaskRepository
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_task_repo_create_task(task_repo, pool):
    """create must insert a background task with pending status."""
    task_id = f"task-create-{uuid4()}"
    task_repo.create(task_id, "ingest", doc_hash="abc123", filename="book.pdf")
    try:
        row = _get_task_raw(pool, task_id)
        assert row is not None
        assert row["task_type"] == "ingest"
        assert row["status"] == "pending"
        assert row["progress_pct"] == 0
        assert row["doc_hash"] == "abc123"
    finally:
        _delete_task(pool, task_id)


@pytest.mark.integration
def test_task_repo_update_status(task_repo, pool):
    """update_status must modify status, progress and progress_pct."""
    task_id = f"task-upd-{uuid4()}"
    task_repo.create(task_id, "summarize")
    try:
        task_repo.update_status(task_id, "running", "Processing chapter 1", 25)
        row = _get_task_raw(pool, task_id)
        assert row["status"] == "running"
        assert row["progress"] == "Processing chapter 1"
        assert row["progress_pct"] == 25

        task_repo.update_status(task_id, "completed", "Done", 100)
        row = _get_task_raw(pool, task_id)
        assert row["status"] == "completed"
        assert row["progress_pct"] == 100
    finally:
        _delete_task(pool, task_id)


@pytest.mark.integration
def test_task_repo_list_active(task_repo, pool):
    """list_active must return only pending and running tasks."""
    t1 = f"task-active-1-{uuid4()}"
    t2 = f"task-active-2-{uuid4()}"
    t3 = f"task-active-3-{uuid4()}"
    task_repo.create(t1, "ingest")
    task_repo.create(t2, "summarize")
    task_repo.create(t3, "generate")
    try:
        task_repo.update_status(t2, "running")
        task_repo.update_status(t3, "completed")

        active = task_repo.list_active()
        ids = {r["task_id"] for r in active}
        assert t1 in ids
        assert t2 in ids
        assert t3 not in ids
    finally:
        for t in (t1, t2, t3):
            _delete_task(pool, t)


@pytest.mark.integration
def test_task_repo_fail_orphaned(task_repo, pool):
    """fail_orphaned must mark all pending/running tasks as failed."""
    t1 = f"task-orphan-1-{uuid4()}"
    t2 = f"task-orphan-2-{uuid4()}"
    t3 = f"task-orphan-3-{uuid4()}"
    task_repo.create(t1, "ingest")
    task_repo.create(t2, "ingest")
    task_repo.create(t3, "ingest")
    try:
        task_repo.update_status(t2, "running")
        task_repo.update_status(t3, "completed")

        task_repo.fail_orphaned()

        row1 = _get_task_raw(pool, t1)
        row2 = _get_task_raw(pool, t2)
        row3 = _get_task_raw(pool, t3)
        assert row1["status"] == "failed"
        assert row1["error"] is not None
        assert row2["status"] == "failed"
        assert row3["status"] == "completed"
    finally:
        for t in (t1, t2, t3):
            _delete_task(pool, t)


@pytest.mark.integration
def test_task_repo_update_status_with_result_and_error(task_repo, pool):
    """update_status must persist JSON result and error text."""
    task_id = f"task-res-{uuid4()}"
    task_repo.create(task_id, "ingest")
    try:
        result = {"tree_id": str(uuid4()), "chapters": 5}
        task_repo.update_status(
            task_id, "failed", "Failed at step 2", 50, result=result, error="Timeout"
        )
        row = _get_task_raw(pool, task_id)
        assert row["result"] == result
        assert row["error"] == "Timeout"
    finally:
        _delete_task(pool, task_id)


@pytest.mark.integration
def test_task_repo_create_on_conflict_ignored(task_repo, pool):
    """create must ignore duplicate task_ids (ON CONFLICT DO NOTHING)."""
    task_id = f"task-dup-{uuid4()}"
    task_repo.create(task_id, "ingest", filename="first.pdf")
    task_repo.create(task_id, "ingest", filename="second.pdf")
    try:
        row = _get_task_raw(pool, task_id)
        assert row["filename"] == "first.pdf"
    finally:
        _delete_task(pool, task_id)
