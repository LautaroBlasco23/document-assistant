"""In-memory task registry with ThreadPoolExecutor for background operations."""

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

from core.exceptions import RateLimitError
from infrastructure.llm.task_context import _current_task

if TYPE_CHECKING:
    from infrastructure.db.task_repository import TaskRepository

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a background task with status and progress."""

    task_id: str
    task_type: str
    doc_hash: str = ""
    filename: str = ""
    chapter: int = 0
    book_title: str = ""
    status: str = "pending"  # pending | running | completed | failed | rate_limited | cancelled
    progress: str = ""
    progress_pct: int = 0  # 0-100 numeric progress percentage
    result: Any = None
    error: str | None = None
    # User-scoped AI call tracking
    user_id: UUID | None = None
    prompt: str = ""
    result_excerpt: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskRegistry:
    """In-memory registry for background tasks with thread pool execution."""

    def __init__(self, max_workers: int = 2, repo: "TaskRepository | None" = None):
        self._tasks: dict[str, Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._repo = repo

    def submit(
        self,
        fn: Callable[..., Any],
        *args,
        task_type: str = "",
        doc_hash: str = "",
        filename: str = "",
        chapter: int = 0,
        book_title: str = "",
        user_id: UUID | None = None,
        prompt: str = "",
        **kwargs,
    ) -> str:
        """
        Submit a callable to execute in background.
        The first argument should be a Task object for status updates.
        Returns task_id.
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            doc_hash=doc_hash,
            filename=filename,
            chapter=chapter,
            book_title=book_title,
            user_id=user_id,
            prompt=prompt,
        )
        self._tasks[task_id] = task

        if self._repo:
            self._repo.create(
                task_id=task_id,
                task_type=task_type,
                doc_hash=doc_hash,
                filename=filename,
                chapter=chapter,
                book_title=book_title,
                user_id=user_id,
                prompt=prompt,
            )

        logger.info("Task submitted: %s (%s)", task_id, fn.__name__)

        def _wrapper() -> None:
            token = _current_task.set(task)
            t0 = time.perf_counter()
            try:
                task.status = "running"
                task.started_at = datetime.now(timezone.utc)
                self._persist(task)
                logger.info("Task started: %s", task_id)
                result = fn(task, *args, **kwargs)
                elapsed = time.perf_counter() - t0
                if task.result is None:
                    task.result = result
                task.status = "completed"
                task.finished_at = datetime.now(timezone.utc)
                self._persist(task)
                logger.info("Task completed: %s (%.1fs)", task_id, elapsed)
            except RateLimitError as e:
                elapsed = time.perf_counter() - t0
                task.error = f"Rate limited by {e.provider} — retry after {int(e.retry_after)}s"
                task.status = "rate_limited"
                task.finished_at = datetime.now(timezone.utc)
                task.result = {"retry_after": e.retry_after, "provider": e.provider}
                self._persist(task)
                logger.warning("Task %s rate-limited after %.1fs: %s", task_id, elapsed, e)
            except Exception as e:
                elapsed = time.perf_counter() - t0
                task.error = str(e)
                task.status = "failed"
                task.finished_at = datetime.now(timezone.utc)
                self._persist(task)
                logger.exception("Task %s failed after %.1fs: %s", task_id, elapsed, e)
            finally:
                _current_task.reset(token)

        self._executor.submit(_wrapper)
        return task_id

    def _persist(self, task: Task) -> None:
        if self._repo:
            self._repo.update_status(
                task_id=task.task_id,
                status=task.status,
                progress=task.progress,
                progress_pct=task.progress_pct,
                result=task.result if isinstance(task.result, dict) else None,
                error=task.error,
                result_excerpt=task.result_excerpt,
                started_at=task.started_at,
                finished_at=task.finished_at,
            )

    def get(self, task_id: str) -> Task | None:
        """Get task status and result."""
        return self._tasks.get(task_id)

    def list_active(self) -> list[Task]:
        """List all pending/running tasks (excludes terminal: completed, failed, rate_limited)."""
        return [t for t in self._tasks.values() if t.status in ("pending", "running")]

    def list_active_for_user(self, user_id: UUID) -> list[Task]:
        """List pending/running tasks for a specific user."""
        return [
            t for t in self._tasks.values()
            if t.status in ("pending", "running") and t.user_id == user_id
        ]

    def shutdown(self) -> None:
        """Shutdown executor, waiting for pending tasks."""
        self._executor.shutdown(wait=True)


def set_task_progress(task: Task, pct: int, message: str) -> None:
    """Update task progress percentage and message, clamped to 0-100."""
    task.progress_pct = max(0, min(100, pct))
    task.progress = message
    logger.debug("Progress [%d%%]: %s", task.progress_pct, message)
