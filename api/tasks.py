"""In-memory task registry with ThreadPoolExecutor for background operations."""

import logging
import time
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
        logger.info("Task submitted: %s (%s)", task_id, fn.__name__)

        def _wrapper() -> None:
            t0 = time.perf_counter()
            try:
                task.status = "running"
                logger.info("Task started: %s", task_id)
                result = fn(task, *args, **kwargs)
                elapsed = time.perf_counter() - t0
                task.result = result
                task.status = "completed"
                logger.info("Task completed: %s (%.1fs)", task_id, elapsed)
            except Exception as e:
                elapsed = time.perf_counter() - t0
                task.error = str(e)
                task.status = "failed"
                logger.exception("Task %s failed after %.1fs: %s", task_id, elapsed, e)

        self._executor.submit(_wrapper)
        return task_id

    def get(self, task_id: str) -> Task | None:
        """Get task status and result."""
        return self._tasks.get(task_id)

    def shutdown(self) -> None:
        """Shutdown executor, waiting for pending tasks."""
        self._executor.shutdown(wait=True)
