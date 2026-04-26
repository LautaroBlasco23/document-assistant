"""
Unit tests for the in-memory task registry.

Subject: api/tasks.py — TaskRegistry, Task
Scope:   Task submission, status retrieval, active listing, and lifecycle transitions.
Out of scope:
  - TaskRepository DB persistence            → test_task_repository.py (integration)
  - Router integration                       → test_tasks_router.py
  - Background task execution at scale       → not tested (handled by ThreadPoolExecutor)
Setup:   In-memory TaskRegistry with 1 worker to avoid thread contention.
"""

import threading
import time
from unittest.mock import MagicMock

import pytest

from api.tasks import TaskRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    """A fresh TaskRegistry with a single worker for deterministic ordering."""
    return TaskRegistry(max_workers=1)


@pytest.fixture
def registry_with_mock_repo():
    """A TaskRegistry backed by a mock TaskRepository to verify persistence calls."""
    repo = MagicMock()
    return TaskRegistry(max_workers=1, repo=repo), repo


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------


def test_submit_returns_task_id(registry):
    """submit() must return a non-empty UUID-like string."""
    task_id = registry.submit(lambda t: None, task_type="ingest")

    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_submit_stores_task_immediately(registry):
    """The task must be retrievable via get() immediately after submission."""
    blocker = threading.Event()

    def _block(t):
        blocker.wait(timeout=2)

    # Occupy the single worker so the next task stays pending
    registry.submit(_block, task_type="blocker")
    task_id = registry.submit(lambda t: None, task_type="ingest", book_title="Test Book")

    task = registry.get(task_id)
    assert task is not None
    assert task.task_id == task_id
    assert task.task_type == "ingest"
    assert task.book_title == "Test Book"
    assert task.status == "pending"

    blocker.set()


def test_submit_passes_extra_metadata(registry):
    """doc_hash, filename, and chapter must be preserved on the Task object."""
    task_id = registry.submit(
        lambda t: None,
        task_type="generate",
        doc_hash="abc123",
        filename="doc.pdf",
        chapter=3,
    )

    task = registry.get(task_id)
    assert task.doc_hash == "abc123"
    assert task.filename == "doc.pdf"
    assert task.chapter == 3


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_returns_none_for_unknown_id(registry):
    """get() must return None when the task_id does not exist."""
    assert registry.get("nonexistent-id") is None


def test_get_returns_correct_task(registry):
    """get() must return the exact Task object matching the provided id."""
    id_a = registry.submit(lambda t: None, task_type="ingest")
    id_b = registry.submit(lambda t: None, task_type="generate")

    assert registry.get(id_a).task_type == "ingest"
    assert registry.get(id_b).task_type == "generate"


# ---------------------------------------------------------------------------
# list_active
# ---------------------------------------------------------------------------


def test_list_active_includes_pending_and_running(registry):
    """list_active() must return tasks whose status is pending or running."""
    event = threading.Event()

    def _block(t):
        t.status = "running"
        event.wait(timeout=2)

    task_id = registry.submit(_block, task_type="ingest")
    time.sleep(0.05)  # Give the worker a moment to start

    active = registry.list_active()
    assert len(active) == 1
    assert active[0].task_id == task_id
    assert active[0].status in ("pending", "running")

    event.set()


def test_list_active_excludes_completed(registry):
    """list_active() must not include tasks that have finished successfully."""
    event = threading.Event()

    def _finish(t):
        event.set()

    task_id = registry.submit(_finish, task_type="ingest")
    event.wait(timeout=2)
    time.sleep(0.05)

    active = registry.list_active()
    assert all(t.task_id != task_id for t in active)
    assert registry.get(task_id).status == "completed"


def test_list_active_excludes_failed(registry):
    """list_active() must not include tasks that failed with an exception."""
    event = threading.Event()

    def _fail(t):
        event.set()
        raise RuntimeError("boom")

    task_id = registry.submit(_fail, task_type="ingest")
    event.wait(timeout=2)
    time.sleep(0.05)

    active = registry.list_active()
    assert all(t.task_id != task_id for t in active)
    assert registry.get(task_id).status == "failed"


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_status_pending_to_running_to_completed(registry):
    """A normal task must transition pending → running → completed."""
    blocker = threading.Event()
    worker_event = threading.Event()

    def _block(t):
        blocker.wait(timeout=2)

    def _work(t):
        worker_event.set()

    # Occupy the single worker so the test task stays pending
    registry.submit(_block, task_type="blocker")
    task_id = registry.submit(_work, task_type="ingest")

    # Immediately after submit, status is pending
    assert registry.get(task_id).status == "pending"

    blocker.set()
    worker_event.wait(timeout=2)
    time.sleep(0.05)

    assert registry.get(task_id).status == "completed"


def test_status_pending_to_running_to_failed(registry):
    """A task that raises must transition pending → running → failed."""
    event = threading.Event()

    def _work(t):
        event.set()
        raise ValueError("intentional failure")

    task_id = registry.submit(_work, task_type="ingest")
    event.wait(timeout=2)
    time.sleep(0.05)

    task = registry.get(task_id)
    assert task.status == "failed"
    assert "intentional failure" in task.error


# ---------------------------------------------------------------------------
# Progress updates
# ---------------------------------------------------------------------------


def test_progress_updates_are_visible(registry):
    """A task that updates progress fields mid-flight must reflect those values."""
    event = threading.Event()
    checkpoint = threading.Event()

    def _work(t):
        t.progress = "halfway"
        t.progress_pct = 50
        checkpoint.set()
        event.wait(timeout=2)
        t.progress = "done"
        t.progress_pct = 100

    task_id = registry.submit(_work, task_type="ingest")
    checkpoint.wait(timeout=2)

    task = registry.get(task_id)
    assert task.progress == "halfway"
    assert task.progress_pct == 50

    event.set()
    time.sleep(0.05)

    task = registry.get(task_id)
    assert task.progress == "done"
    assert task.progress_pct == 100


# ---------------------------------------------------------------------------
# Result capture
# ---------------------------------------------------------------------------


def test_result_captured_when_fn_returns(registry):
    """The return value of the wrapped function must be stored in task.result."""
    event = threading.Event()

    def _work(t):
        event.set()
        return {"tree_id": "abc"}

    task_id = registry.submit(_work, task_type="ingest")
    event.wait(timeout=2)
    time.sleep(0.05)

    assert registry.get(task_id).result == {"tree_id": "abc"}


def test_result_not_overwritten_if_already_set(registry):
    """If the task callback sets result manually, the wrapper must not replace it."""
    event = threading.Event()

    def _work(t):
        t.result = {"custom": True}
        event.set()
        return {"from_fn": True}

    task_id = registry.submit(_work, task_type="ingest")
    event.wait(timeout=2)
    time.sleep(0.05)

    assert registry.get(task_id).result == {"custom": True}


# ---------------------------------------------------------------------------
# Persistence integration (mock repo)
# ---------------------------------------------------------------------------


def test_submit_calls_repo_create(registry_with_mock_repo):
    """When a repo is provided, submit() must persist the initial task record."""
    registry, repo = registry_with_mock_repo
    registry.submit(lambda t: None, task_type="ingest", doc_hash="hash1")

    assert repo.create.called
    kwargs = repo.create.call_args.kwargs
    assert kwargs["task_type"] == "ingest"
    assert kwargs["doc_hash"] == "hash1"


def test_status_transition_calls_repo_update(registry_with_mock_repo):
    """When a repo is provided, status changes must trigger update_status."""
    registry, repo = registry_with_mock_repo
    event = threading.Event()

    def _work(t):
        event.set()

    task_id = registry.submit(_work, task_type="ingest")
    event.wait(timeout=2)
    time.sleep(0.1)

    # At least pending → running → completed means multiple update calls
    update_calls = [
        c for c in repo.update_status.call_args_list if c.kwargs.get("task_id") == task_id
    ]
    assert len(update_calls) >= 2


# ---------------------------------------------------------------------------
# shutdown
# ---------------------------------------------------------------------------


def test_shutdown_does_not_raise(registry):
    """shutdown() must complete gracefully even with no submitted tasks."""
    registry.shutdown()


def test_shutdown_waits_for_pending(registry):
    """shutdown(wait=True) must allow active tasks to finish before returning."""
    event = threading.Event()

    def _work(t):
        time.sleep(0.05)
        event.set()

    task_id = registry.submit(_work, task_type="ingest")
    registry.shutdown()

    assert event.is_set()
    assert registry.get(task_id).status == "completed"
