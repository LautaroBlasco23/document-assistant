"""Background task for text/formatting improvement."""

import logging
import re
import time
from uuid import UUID

from api.services import Services
from api.tasks import Task, set_task_progress
from application.agents.text_chunker import TextChunker
from application.agents.text_improvement import TextImprovementAgent
from application.llm_resolver import resolve_llm_for_agent
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)

# Delay between chunk API calls to stay under Groq's 30 RPM limit.
# 60s / 30 RPM = 2.0s per request minimum; use 2.5s for safety margin.
_CHUNK_DELAY_SECONDS = 2.5


def _clean_residual_markers(text: str) -> str:
    """Remove any __HEADING__ / __SUBHEADING__ markers the LLM failed to convert."""
    text = re.sub(r"__HEADING__(.*?)__END_HEADING__", r"## \1", text)
    text = re.sub(r"__SUBHEADING__(.*?)__END_SUBHEADING__", r"### \1", text)
    return text


def _join_chunks(improved_parts: list[str], chunks: list[dict]) -> str:
    """Join improved chunks, removing overlap duplicates from all but the first chunk.

    The first chunk is kept as-is. For subsequent chunks, we try to find and remove
    the overlap context that was included for continuity.
    """
    if not improved_parts:
        return ""

    if len(improved_parts) == 1:
        return improved_parts[0]

    result_parts: list[str] = [improved_parts[0]]

    for i in range(1, len(improved_parts)):
        improved = improved_parts[i]
        context = chunks[i].get("context")

        if context and improved:
            # Try to remove the overlap context from the beginning of the improved text.
            # The LLM may have repeated some or all of the context.
            overlap_end = _find_overlap_end(improved, context)
            if overlap_end > 0:
                improved = improved[overlap_end:].lstrip("\n")
                logger.debug(
                    "Chunk %d: stripped %d chars of overlap context", i, overlap_end
                )

        result_parts.append(improved)

    return "\n\n".join(result_parts)


def _find_overlap_end(text: str, context: str) -> int:
    """Find where the overlap context ends in the improved text.

    Tries to match the last paragraph of the context at the start of the text.
    Returns the index where the actual content begins, or 0 if no match found.
    """
    if not context:
        return 0

    # Get the last meaningful paragraph from context
    context_paras = [p.strip() for p in context.split("\n\n") if p.strip()]
    if not context_paras:
        return 0

    last_context_para = context_paras[-1]
    text_lower = text.lower()
    context_lower = last_context_para.lower()

    # Try to find the context paragraph (or a close match) at the start of the text
    idx = text_lower.find(context_lower)
    if idx == 0:
        # Exact match at start — skip past it
        return len(last_context_para)

    # Try with first few words of the context paragraph (partial match)
    first_words = " ".join(context_lower.split()[:5])
    if len(first_words) > 10:
        idx = text_lower.find(first_words)
        if idx == 0:
            # Found the start of the context — find where it ends
            # Look for the next paragraph break after the context
            remaining = text[len(first_words):]
            para_break = remaining.find("\n\n")
            if para_break >= 0:
                return len(first_words) + para_break + 2

    return 0


def improve_document_task(
    task: Task,
    doc_uid: UUID,
    tree_id: UUID,
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

    label = "Reformatting document..."
    set_task_progress(task, 20, label)

    agent = TextImprovementAgent(llm)

    # Check if document needs chunking (for token-limited providers like Groq)
    chunk_cfg = services.config.chunking
    chunker = TextChunker(
        max_tokens=chunk_cfg.improve_max_tokens,
        overlap_tokens=chunk_cfg.improve_overlap_tokens,
    )

    if chunker.should_chunk(doc.content):
        # Chunked processing for large documents
        chunks = chunker.chunk(doc.content)
        total_chunks = len(chunks)
        improved_parts: list[str] = []

        for i, chunk in enumerate(chunks):
            progress = 20 + int(60 * (i / total_chunks))
            set_task_progress(
                task, progress,
                f"{label} (chunk {i + 1}/{total_chunks})..."
            )

            # Rate limit: delay between chunk API calls to stay under RPM limit
            if i > 0:
                time.sleep(_CHUNK_DELAY_SECONDS)

            # Per-chunk max_tokens: estimate from chunk size, cap at 2048
            # Total tokens (input + output + system prompt ~500) must stay under 6000.
            chunk_tokens = len(chunk["text"].split())
            chunk_max = min(int(chunk_tokens * 1.0), 2048)
            chunk_params = GenerationParams(
                temperature=params.temperature,
                top_p=params.top_p,
                max_tokens=max(chunk_max, 512),
            )

            improved_chunk = agent.improve(
                chunk["text"],
                params=chunk_params,
                agent_prompt=agent_prompt,
                context=chunk["context"],
            )
            improved_parts.append(improved_chunk)

        # Join results: first chunk as-is, subsequent chunks need overlap dedup
        improved = _join_chunks(improved_parts, chunks)
        logger.info(
            "Document improved in %d chunks (%d -> %d chars)",
            total_chunks, len(doc.content), len(improved),
        )
    else:
        # Single-call path for small documents
        improved = agent.improve(doc.content, params=params, agent_prompt=agent_prompt)

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
