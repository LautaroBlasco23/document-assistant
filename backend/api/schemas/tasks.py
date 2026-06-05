"""Task tracking schemas."""

from pydantic import BaseModel


class TaskStatusOut(BaseModel):
    """Status of a background task."""

    task_id: str
    status: str  # pending | running | completed | failed | rate_limited | cancelled
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


class TaskHistoryItem(BaseModel):
    """A single task row for the AI calls history tab."""

    task_id: str
    task_type: str
    status: str
    progress: str = ""
    progress_pct: int = 0
    chapter: int = 0
    book_title: str = ""
    prompt: str = ""
    result_excerpt: str = ""
    error: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class TaskListOut(BaseModel):
    """Paginated response for GET /api/tasks/recent."""

    tasks: list[TaskHistoryItem]
    total: int
    has_more: bool
