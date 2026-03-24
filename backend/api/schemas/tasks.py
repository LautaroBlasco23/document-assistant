"""Task tracking schemas."""

from pydantic import BaseModel


class TaskStatusOut(BaseModel):
    """Status of a background task."""

    task_id: str
    status: str  # pending | running | completed | failed
    progress: str = ""
    progress_pct: int = 0
    result: dict | None = None
    error: str | None = None


class ActiveTaskOut(BaseModel):
    """An active (non-terminal) task returned by GET /api/tasks/active."""

    task_id: str
    task_type: str
    doc_hash: str
    filename: str
    status: str
    progress: str = ""
    progress_pct: int = 0
    chapter: int = 0
    book_title: str = ""


class ActiveTasksOut(BaseModel):
    """Response for GET /api/tasks/active."""

    tasks: list[ActiveTaskOut]
