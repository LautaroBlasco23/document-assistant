"""Background task for text/formatting improvement."""

import logging
from uuid import UUID

from api.services import Services
from api.tasks import Task, set_task_progress
from application.agents.text_improvement import TextImprovementAgent
from application.llm_resolver import resolve_llm_for_agent
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)


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

    params = GenerationParams(
        temperature=_param(temperature, getattr(agent_params, "temperature", None)),
        top_p=_param(top_p, getattr(agent_params, "top_p", None)),
        max_tokens=_param(max_tokens, getattr(agent_params, "max_tokens", None)),
    )

    label = "Improving document..." if mode == "text" else "Reformatting document..."
    set_task_progress(task, 20, label)

    agent = TextImprovementAgent(llm)
    improved = agent.improve(doc.content, params=params, agent_prompt=agent_prompt, mode=mode)

    set_task_progress(task, 80, "Saving...")
    updated = services.kt_doc_store.save_improvement(doc_uid, improved)

    set_task_progress(task, 100, "Done")
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
