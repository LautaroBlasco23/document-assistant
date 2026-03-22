"""Task status endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from api.deps import ServicesDep
from api.schemas.tasks import TaskStatusOut

logger = logging.getLogger(__name__)

router = APIRouter()


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
