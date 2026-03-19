"""Task tracking schemas."""

from pydantic import BaseModel


class TaskStatusOut(BaseModel):
    """Status of a background task."""

    task_id: str
    status: str  # pending | running | completed | failed
    progress: str = ""
    result: dict | None = None
    error: str | None = None
