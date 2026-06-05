"""Background task for text/formatting improvement."""

import logging
import re
from uuid import UUID

from api.services import Services
from api.tasks import Task, set_task_progress
from application.agents.text_improvement import TextImprovementAgent
from application.llm_resolver import resolve_llm_for_agent
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)


def _clean_residual_markers(text: str) -> str:
    """Remove any __HEADING__ / __SUBHEADING__ markers the LLM failed to convert."""
    text = re.sub(r"__HEADING__(.*?)__END_HEADING__", r"## \1", text)
    text = re.sub(r"__SUBHEADING__(.*?)__END_SUBHEADING__", r"### \1", text)
    return text


def improve_document_task(
    task: Task,
    doc_uid: UUID,
    tree_id: UUID,
    mode: str,
    services: Services,
    user_id: UUID,
    agent_id: UUID | None = None,
    model_override: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
) -> dict:
    """Background task: improve document text or formatting via LLM."""
    set_task_progress(task, 5, "Resolving AI provider...")

    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != tree_id:
        raise ValueError("Knowledge document not found")
    if not doc.content or not doc.content.strip():
        raise ValueError("Document has no content to improve")

    llm, agent_prompt, agent_params = resolve_llm_for_agent(
        user_id,
        agent_id,
        services,
        model_override=model_override,
    )

    def _param(value: float | None, fallback: float | None) -> float | None:
        return value if value is not None else fallback

    # Dynamic max_tokens: estimate based on input length to avoid truncation
    input_chars = len(doc.content)
    input_token_estimate = max(input_chars // 4, 512)  # rough: 1 token ≈ 4 chars
    dynamic_max = min(int(input_token_estimate * 1.5), 32768)  # 1.5x input, cap 32K

    params = GenerationParams(
        temperature=_param(temperature, getattr(agent_params, "temperature", None)),
        top_p=_param(top_p, getattr(agent_params, "top_p", None)),
        max_tokens=max(dynamic_max, max_tokens) if max_tokens else dynamic_max,
    )

    label = "Improving document..." if mode == "text" else "Reformatting document..."
    set_task_progress(task, 20, label)

    agent = TextImprovementAgent(llm)
    improved = agent.improve(doc.content, params=params, agent_prompt=agent_prompt, mode=mode)

    # Defensive check: ensure we got a valid string
    if not improved or not isinstance(improved, str):
        raise ValueError(
            f"LLM returned invalid response (type: {type(improved).__name__}, "
            f"value: {repr(improved)[:100]})"
        )

    # Post-processing: clean up any residual markers the LLM missed
    improved = _clean_residual_markers(improved)

    # Validate output length — warn if severely truncated
    input_len = len(doc.content)
    output_len = len(improved)
    if output_len < input_len * 0.5:
        logger.warning(
            "Improve output is %.0f%% of input length (%d vs %d chars). "
            "Response may have been truncated by the LLM.",
            output_len / input_len * 100, output_len, input_len,
        )

    set_task_progress(task, 80, "Saving...")
    updated = services.kt_doc_store.save_improvement(doc_uid, improved)

    set_task_progress(task, 100, "Done")
    task.result_excerpt = improved[:500]
    return {
        "id": str(updated.id),
        "tree_id": str(updated.tree_id),
        "chapter_id": str(updated.chapter_id) if updated.chapter_id else None,
        "chapter_number": updated.chapter_number,
        "title": updated.title,
        "content": updated.content,
        "original_content": updated.original_content,
        "is_main": updated.is_main,
        "created_at": updated.created_at.isoformat(),
        "updated_at": updated.updated_at.isoformat(),
        "source_file_path": updated.source_file_path,
        "source_file_name": updated.source_file_name,
        "page_start": updated.page_start,
        "page_end": updated.page_end,
        "source_type": updated.source_type,
        "source_url": updated.source_url,
        "file_type": updated.file_type,
    }
