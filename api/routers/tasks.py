"""Task status endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from api.deps import ServicesDep
from api.schemas.tasks import ActiveTaskOut, ActiveTasksOut, TaskStatusOut

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tasks/active", response_model=ActiveTasksOut)
async def list_active_tasks(services: ServicesDep) -> ActiveTasksOut:
    """List all non-terminal tasks (pending/running)."""
    from infrastructure.db.task_repository import TaskRepository

    repo = TaskRepository(services._pg_pool)
    rows = repo.list_active()
    return ActiveTasksOut(
        tasks=[
            ActiveTaskOut(
                task_id=row["task_id"],
                task_type=row["task_type"],
                doc_hash=row["doc_hash"] or "",
                filename=row["filename"] or "",
                status=row["status"],
                progress=row["progress"] or "",
                progress_pct=row["progress_pct"] or 0,
                chapter=row.get("chapter") or 0,
                book_title=row.get("book_title") or "",
            )
            for row in rows
        ]
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusOut)
async def get_task_status(task_id: str, services: ServicesDep) -> TaskStatusOut:
    """Get status of a background task."""
    logger.debug("Task status poll: %s", task_id)
    task = services.task_registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusOut(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        progress_pct=task.progress_pct,
        result=task.result if isinstance(task.result, dict) else None,
        error=task.error,
    )
