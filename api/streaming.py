"""Server-Sent Events (SSE) helper for streaming responses."""

import json


def make_sse_event(event_type: str, data: dict | None = None) -> str:
    """
    Create an SSE event string.

    Args:
        event_type: Event type name (e.g., "token", "done")
        data: Dict to serialize as JSON data

    Returns:
        SSE formatted event string (includes trailing newlines)
    """
    lines = [f"event: {event_type}"]
    if data:
        lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # blank line to signal end of event
    return "\n".join(lines) + "\n"
