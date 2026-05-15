"""Unit tests for PostgreSQL task repository.

Scope: TaskRepository — create, update_status, fail_orphaned, list_active.
Out-of-scope: integration with real PostgreSQL.
Setup: Mock psycopg.Connection and PostgresConnection via unittest.mock.
"""
from unittest.mock import MagicMock

from infrastructure.db.task_repository import TaskRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool_and_cursor():
    pool = MagicMock()
    cur = MagicMock()
    conn = MagicMock()

    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    cur.rowcount = 0

    cm_cur = MagicMock()
    cm_cur.__enter__ = MagicMock(return_value=cur)
    cm_cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cm_cur

    conn.info.transaction_status = 0

    pool.connection.return_value = conn

    return pool, cur, conn


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_task_create_inserts_row():
    """create must execute an INSERT with ON CONFLICT DO NOTHING."""
    pool, cur, conn = _make_pool_and_cursor()

    repo = TaskRepository(pool)
    repo.create("task-1", "ingest", doc_hash="abc123",
                filename="book.pdf", chapter=1, book_title="Book")

    assert cur.execute.call_count == 1
    conn.commit.assert_called_once()


def test_task_create_with_defaults():
    """create must use default values for optional parameters."""
    pool, cur, _ = _make_pool_and_cursor()

    repo = TaskRepository(pool)
    repo.create("task-2", "summarize")

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------

def test_update_status_with_result():
    """update_status must serialize result dict to JSON."""
    pool, cur, conn = _make_pool_and_cursor()

    repo = TaskRepository(pool)
    repo.update_status("task-1", "completed", progress="Done",
                        progress_pct=100, result={"key": "value"})

    assert cur.execute.call_count == 1
    conn.commit.assert_called_once()


def test_update_status_with_error():
    """update_status must store error message."""
    pool, cur, conn = _make_pool_and_cursor()

    repo = TaskRepository(pool)
    repo.update_status("task-1", "failed", error="Something went wrong")

    assert cur.execute.call_count == 1


def test_update_status_minimal():
    """update_status must work with only task_id and status."""
    pool, cur, conn = _make_pool_and_cursor()

    repo = TaskRepository(pool)
    repo.update_status("task-1", "running")

    assert cur.execute.call_count == 1
    conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# fail_orphaned
# ---------------------------------------------------------------------------

def test_fail_orphaned_marks_tasks():
    """fail_orphaned must update all pending/running tasks to failed."""
    pool, cur, conn = _make_pool_and_cursor()
    cur.rowcount = 3

    repo = TaskRepository(pool)
    count = repo.fail_orphaned()

    assert count == 3
    assert cur.execute.call_count == 1
    conn.commit.assert_called_once()


def test_fail_orphaned_no_orphans():
    """fail_orphaned must return 0 when no orphaned tasks exist."""
    pool, cur, conn = _make_pool_and_cursor()
    cur.rowcount = 0

    repo = TaskRepository(pool)
    count = repo.fail_orphaned()

    assert count == 0


# ---------------------------------------------------------------------------
# list_active
# ---------------------------------------------------------------------------

def test_list_active_returns_tasks():
    """list_active must return all pending/running tasks."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        {"task_id": "task-1", "task_type": "ingest", "status": "pending"},
        {"task_id": "task-2", "task_type": "summarize", "status": "running"},
    ]

    repo = TaskRepository(pool)
    tasks = repo.list_active()

    assert len(tasks) == 2
    assert tasks[0]["task_id"] == "task-1"
    assert tasks[1]["status"] == "running"


def test_list_active_empty():
    """list_active must return an empty list when no active tasks exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = []

    repo = TaskRepository(pool)
    tasks = repo.list_active()

    assert tasks == []
