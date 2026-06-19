"""Background task for creating optimized study documents."""

import logging
import time
from uuid import UUID, uuid4

from api.services import Services
from api.tasks import Task, set_task_progress
from application.agents.document_optimizer import DocumentOptimizerAgent
from application.agents.text_chunker import TextChunker
from application.llm_resolver import resolve_llm_for_agent
from application.services.text_improvement import _join_chunks
from core.model.knowledge_tree import KnowledgeChunk
from core.ports.llm import GenerationParams

logger = logging.getLogger(__name__)

# Delay between chunk API calls to stay under rate limits.
_CHUNK_DELAY_SECONDS = 2.5


def optimize_document_task(
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
    """Background task: create an optimized study document and add it to the same chapter.

    Creates a NEW knowledge document (separate from the source) containing a
    summarized/reorganized version with suggested questions at the end.
    """
    set_task_progress(task, 5, "Resolving AI provider...")

    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != tree_id:
        raise ValueError("Knowledge document not found")
    if not doc.content or not doc.content.strip():
        raise ValueError("Document has no content to optimize")

    llm, agent_prompt, agent_params = resolve_llm_for_agent(
        user_id,
        agent_id,
        services,
        model_override=model_override,
    )

    def _param(value: float | None, fallback: float | None) -> float | None:
        return value if value is not None else fallback

    # Dynamic max_tokens: estimate based on input length
    input_chars = len(doc.content)
    input_token_estimate = max(input_chars // 4, 512)
    dynamic_max = min(int(input_token_estimate * 1.5), 32768)

    params = GenerationParams(
        temperature=_param(temperature, getattr(agent_params, "temperature", None)),
        top_p=_param(top_p, getattr(agent_params, "top_p", None)),
        max_tokens=max(dynamic_max, max_tokens) if max_tokens else dynamic_max,
    )

    set_task_progress(task, 20, "Optimizing document...")

    agent = DocumentOptimizerAgent(llm)

    # Check if document needs chunking
    chunk_cfg = services.config.chunking
    chunker = TextChunker(
        max_tokens=chunk_cfg.optimize_max_tokens,
        overlap_tokens=chunk_cfg.optimize_overlap_tokens,
    )

    if chunker.should_chunk(doc.content):
        # Chunked processing for large documents
        chunks = chunker.chunk(doc.content)
        total_chunks = len(chunks)
        optimized_parts: list[str] = []

        for i, chunk in enumerate(chunks):
            progress = 20 + int(60 * (i / total_chunks))
            set_task_progress(
                task, progress,
                f"Optimizing document... (chunk {i + 1}/{total_chunks})..."
            )

            if i > 0:
                time.sleep(_CHUNK_DELAY_SECONDS)

            chunk_tokens = len(chunk["text"].split())
            chunk_max = min(int(chunk_tokens * 1.5), 4096)
            chunk_params = GenerationParams(
                temperature=params.temperature,
                top_p=params.top_p,
                max_tokens=max(chunk_max, 512),
            )

            optimized_chunk = agent.optimize(
                chunk["text"],
                params=chunk_params,
                agent_prompt=agent_prompt,
                context=chunk["context"],
            )
            optimized_parts.append(optimized_chunk)

        # Join results: first chunk as-is, subsequent chunks need overlap dedup
        optimized = _join_chunks(optimized_parts, chunks)
        logger.info(
            "Document optimized in %d chunks (%d -> %d chars)",
            total_chunks, len(doc.content), len(optimized),
        )
    else:
        optimized = agent.optimize(doc.content, params=params, agent_prompt=agent_prompt)

    if not optimized or not isinstance(optimized, str):
        raise ValueError(
            f"LLM returned invalid response (type: {type(optimized).__name__})"
        )

    # Validate output length — warn if severely truncated
    if len(optimized) < len(doc.content) * 0.2:
        logger.warning(
            "Optimize output is %.0f%% of input length (%d vs %d chars). "
            "Response may have been truncated by the LLM.",
            len(optimized) / len(doc.content) * 100,
            len(optimized),
            len(doc.content),
        )

    set_task_progress(task, 80, "Creating optimized document...")

    # Create a NEW document in the same chapter
    optimized_title = f"{doc.title} (Optimized)"
    new_doc = services.kt_doc_store.create_document(
        tree_id=tree_id,
        chapter_id=doc.chapter_id,
        title=optimized_title,
        content=optimized,
        is_main=False,
        file_type="md",
    )

    # Chunk the optimized document for search
    from core.model.document import Chapter, Page
    from core.model.document import Document as DocModel

    simple_doc = DocModel(
        source_path="",
        title=optimized_title,
        file_hash="",
        original_filename="",
        chapters=[
            Chapter(
                index=0,
                title=optimized_title,
                pages=[Page(number=1, text=optimized)],
            )
        ],
    )

    from infrastructure.chunking.splitter import ChapterAwareSplitter

    splitter = ChapterAwareSplitter()
    content_chunks = splitter.split(simple_doc)

    kt_chunks = [
        KnowledgeChunk(
            id=uuid4(),
            tree_id=tree_id,
            chapter_id=doc.chapter_id or uuid4(),
            doc_id=new_doc.id,
            chunk_index=j,
            text=c.text,
            token_count=c.token_count,
        )
        for j, c in enumerate(content_chunks)
    ]

    if kt_chunks:
        services.kt_content_store.save_chunks(kt_chunks)

    set_task_progress(task, 100, "Done")
    task.result_excerpt = f"Created optimized document: {optimized_title}"
    logger.info(
        "Created optimized document %s for doc %s in tree %s",
        new_doc.id,
        doc_uid,
        tree_id,
    )

    return {
        "id": str(new_doc.id),
        "tree_id": str(new_doc.tree_id),
        "chapter_id": str(new_doc.chapter_id) if new_doc.chapter_id else None,
        "chapter_number": new_doc.chapter_number,
        "title": new_doc.title,
        "content": new_doc.content,
        "original_content": new_doc.original_content,
        "is_main": new_doc.is_main,
        "created_at": new_doc.created_at.isoformat(),
        "updated_at": new_doc.updated_at.isoformat(),
        "source_file_path": new_doc.source_file_path,
        "source_file_name": new_doc.source_file_name,
        "page_start": new_doc.page_start,
        "page_end": new_doc.page_end,
        "source_type": "optimized",
        "source_url": new_doc.source_url,
        "file_type": new_doc.file_type,
    }
