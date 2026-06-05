"""Task status endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from api.auth import CurrentUser
from api.deps import ServicesDep
from api.schemas.tasks import (
    ActiveTaskOut,
    ActiveTasksOut,
    TaskHistoryItem,
    TaskListOut,
    TaskStatusOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tasks/active", response_model=ActiveTasksOut)
async def list_active_tasks(
    current_user: CurrentUser,
    services: ServicesDep,
) -> ActiveTasksOut:
    """List all non-terminal tasks (pending/running) for the current user."""
    from infrastructure.db.task_repository import TaskRepository

    repo = TaskRepository(services._pg_pool)
    rows = repo.list_active_for_user(current_user.id)
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


@router.get("/tasks/recent", response_model=TaskListOut)
async def list_recent_tasks(
    current_user: CurrentUser,
    services: ServicesDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status"),
) -> TaskListOut:
    """Paginated history of AI tasks for the current user."""
    from infrastructure.db.task_repository import TaskRepository

    repo = TaskRepository(services._pg_pool)
    rows, total = repo.list_for_user(
        current_user.id, limit=limit, offset=offset, status_filter=status
    )
    return TaskListOut(
        tasks=[
            TaskHistoryItem(
                task_id=row["task_id"],
                task_type=row["task_type"],
                status=row["status"],
                progress=row["progress"] or "",
                progress_pct=row["progress_pct"] or 0,
                chapter=row.get("chapter") or 0,
                book_title=row.get("book_title") or "",
                prompt=row["prompt"] or "",
                result_excerpt=row["result_excerpt"] or "",
                error=row.get("error"),
                created_at=row["created_at"].isoformat() if row["created_at"] else "",
                started_at=row["started_at"].isoformat() if row.get("started_at") else None,
                finished_at=row["finished_at"].isoformat() if row.get("finished_at") else None,
            )
            for row in rows
        ],
        total=total,
        has_more=offset + limit < total,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusOut)
async def get_task_status(
    task_id: str,
    current_user: CurrentUser,
    services: ServicesDep,
) -> TaskStatusOut:
    """Get status of a background task (only if owned by current user)."""
    # Try in-memory first (for running tasks)
    task = services.task_registry.get(task_id)
    if task:
        if task.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskStatusOut(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            progress_pct=task.progress_pct,
            result=task.result if isinstance(task.result, dict) else None,
            error=task.error,
        )

    # Fall back to DB (for completed tasks no longer in memory)
    from infrastructure.db.task_repository import TaskRepository

    repo = TaskRepository(services._pg_pool)
    row = repo.get_for_user(task_id, current_user.id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusOut(
        task_id=row["task_id"],
        status=row["status"],
        progress=row["progress"] or "",
        progress_pct=row["progress_pct"] or 0,
        result=None,
        error=row.get("error"),
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: CurrentUser,
    services: ServicesDep,
) -> dict:
    """Best-effort cancel: flip status to cancelled if still running/pending."""
    from infrastructure.db.task_repository import TaskRepository

    repo = TaskRepository(services._pg_pool)
    result = repo.cancel_task(task_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found or already completed")
    return {"task_id": result["task_id"], "status": result["status"]}
