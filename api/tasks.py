"""In-memory task registry with ThreadPoolExecutor for background operations."""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a background task with status and progress."""

    task_id: str
    status: str  # pending | running | completed | failed
    progress: str = ""
    result: Any = None
    error: str | None = None


class TaskRegistry:
    """In-memory registry for background tasks with thread pool execution."""

    def __init__(self, max_workers: int = 2):
        self._tasks: dict[str, Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> str:
        """
        Submit a callable to execute in background.
        The first argument should be a Task object for status updates.
        Returns task_id.
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id=task_id, status="pending")
        self._tasks[task_id] = task

        def _wrapper() -> None:
            try:
                task.status = "running"
                result = fn(task, *args, **kwargs)
                task.result = result
                task.status = "completed"
            except Exception as e:
                task.error = str(e)
                task.status = "failed"
                logger.exception(f"Task {task_id} failed: {e}")

        self._executor.submit(_wrapper)
        return task_id

    def get(self, task_id: str) -> Task | None:
        """Get task status and result."""
        return self._tasks.get(task_id)

    def shutdown(self) -> None:
        """Shutdown executor, waiting for pending tasks."""
        self._executor.shutdown(wait=True)
