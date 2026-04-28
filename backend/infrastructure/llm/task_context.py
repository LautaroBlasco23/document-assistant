from contextvars import ContextVar
from typing import Any

# Holds a reference to the current background Task during executor runs.
# Set by TaskRegistry._wrapper() so that LLM providers can write progress
# updates directly to the task during long 429 sleeps.
_current_task: ContextVar[Any] = ContextVar("_current_task", default=None)
