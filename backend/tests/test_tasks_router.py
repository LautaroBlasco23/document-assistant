"""
Unit tests for the task status router (/api/tasks/*).

Subject: api/routers/tasks.py
Scope:   Listing active tasks and fetching individual task status.
Out of scope:
  - TaskRegistry internals                     → test_task_registry.py
  - TaskRepository DB operations               → test_task_repository.py (integration)
  - Background task execution lifecycle        → test_knowledge_trees.py (integration)
Setup:   FastAPI TestClient with mocked services and TaskRepository.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import get_services_dep
from api.routers import tasks as tasks_router
from api.tasks import Task, TaskRegistry
from core.model.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


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


@pytest.fixture
def mock_services():
    """Return a Services-like object with an in-memory TaskRegistry."""
    services = MagicMock()
    services.task_registry = TaskRegistry(max_workers=1)
    services._pg_pool = MagicMock()
    return services


@pytest.fixture
def test_client(mock_services):
    """Build a FastAPI test app with the tasks router and mocked services."""
    app = FastAPI()
    app.include_router(tasks_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/tasks/active
# ---------------------------------------------------------------------------


def test_list_active_tasks_returns_pending_and_running(test_client, mock_services):
    """GET /api/tasks/active must return tasks that are pending or running."""
    with patch(
        "infrastructure.db.task_repository.TaskRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.list_active.return_value = [
            {
                "task_id": "task-1",
                "task_type": "ingest",
                "doc_hash": "abc",
                "filename": "book.pdf",
                "status": "pending",
                "progress": "",
                "progress_pct": 0,
                "chapter": 1,
                "book_title": "My Book",
            },
            {
                "task_id": "task-2",
                "task_type": "generate",
                "doc_hash": "def",
                "filename": "doc.pdf",
                "status": "running",
                "progress": "50%",
                "progress_pct": 50,
                "chapter": 2,
                "book_title": "Another Book",
            },
        ]
        mock_repo_cls.return_value = mock_repo

        response = test_client.get("/api/tasks/active")

    assert response.status_code == 200
    body = response.json()
    assert len(body["tasks"]) == 2
    assert body["tasks"][0]["task_id"] == "task-1"
    assert body["tasks"][1]["task_id"] == "task-2"
    assert body["tasks"][1]["progress_pct"] == 50


def test_list_active_tasks_empty_when_none_active(test_client, mock_services):
    """When no tasks are pending or running, the endpoint must return an empty list."""
    with patch(
        "infrastructure.db.task_repository.TaskRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.list_active.return_value = []
        mock_repo_cls.return_value = mock_repo

        response = test_client.get("/api/tasks/active")

    assert response.status_code == 200
    assert response.json()["tasks"] == []


# ---------------------------------------------------------------------------
# GET /api/tasks/{id}
# ---------------------------------------------------------------------------


def test_get_task_pending_returns_status(test_client, mock_services):
    """GET /api/tasks/{id} for a pending task must return its status."""
    import threading

    event = threading.Event()

    def _block(t):
        event.wait(timeout=2)

    task_id = mock_services.task_registry.submit(
        _block, task_type="ingest", book_title="Test"
    )
    response = test_client.get(f"/api/tasks/{task_id}")

    event.set()

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["status"] in ("pending", "running")


def test_get_task_completed_returns_result(test_client, mock_services):
    """GET /api/tasks/{id} for a completed task must include its result."""
    import threading

    event = threading.Event()

    def _complete(t):
        t.result = {"tree_id": "123"}
        event.set()

    task_id = mock_services.task_registry.submit(
        _complete, task_type="ingest"
    )
    event.wait(timeout=2)

    response = test_client.get(f"/api/tasks/{task_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["status"] == "completed"
    assert body["result"] == {"tree_id": "123"}


def test_get_task_failed_returns_error(test_client, mock_services):
    """GET /api/tasks/{id} for a failed task must include the error message."""
    def _fail(t):
        raise RuntimeError("something went wrong")

    # We can't easily wait for failure in the registry, but we can inject a failed task directly.
    task_id = "failed-task-1"
    mock_services.task_registry._tasks[task_id] = Task(
        task_id=task_id,
        task_type="ingest",
        status="failed",
        error="something went wrong",
    )

    response = test_client.get(f"/api/tasks/{task_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"] == "something went wrong"


def test_get_task_unknown_returns_404(test_client):
    """GET /api/tasks/{id} for a nonexistent task must return 404."""
    response = test_client.get("/api/tasks/does-not-exist")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
