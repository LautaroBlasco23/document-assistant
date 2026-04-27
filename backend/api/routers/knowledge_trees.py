"""Knowledge Tree endpoints."""

import hashlib
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import fitz  # PyMuPDF
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep
from api.limit_checks import PlanLimitExceeded, check_can_create_tree
from api.schemas.knowledge_tree import (
    ChapterPreviewOut,
    CreateChapterRequest,
    CreateDocumentRequest,
    CreateExamSessionRequest,
    CreateTreeRequest,
    DocumentPreviewOut,
    ExamSessionOut,
    KnowledgeChapterOut,
    KnowledgeChunkOut,
    KnowledgeDocumentOut,
    KnowledgeTreeOut,
    UpdateChapterRequest,
    UpdateDocumentRequest,
    UpdateTreeRequest,
)
from api.schemas.question import GenerateQuestionsRequest, QuestionOut
from api.tasks import Task
from application.agents._batching import chunks_around_selection
from application.agents._tokens import truncate_tokens
from application.agents.flashcard_generator import FlashcardGeneratorAgent
from application.agents.question_generator import QuestionGeneratorAgent
from core.model.chunk import Chunk, ChunkMetadata
from core.model.knowledge_tree import ExamSession, Flashcard, KnowledgeChunk
from core.model.question import Question, QuestionType
from infrastructure.chunking.splitter import ChapterAwareSplitter
from infrastructure.config import PROJECT_ROOT
from infrastructure.ingest.epub_loader import preview_epub
from infrastructure.ingest.pdf_loader import preview_pdf
from infrastructure.llm.factory import create_llm_with_model

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helpers for agent resolution
# ---------------------------------------------------------------------------

def _resolve_agent_llm(
    services: ServicesDep,
    model: str | None,
    agent_id: str | None,
    fallback_llm,
):
    """Resolve agent, returning (llm, agent_prompt | None)."""
    if agent_id:
        try:
            agent_uid = UUID(agent_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid agent_id")
        agent = services.agent_store.get_by_id(agent_uid)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return create_llm_with_model(services.config, agent.model), agent.prompt
    if model:
        return create_llm_with_model(services.config, model), None
    return fallback_llm, None


def _resolve_agent_params(
    services: ServicesDep,
    body_temperature: float | None,
    body_top_p: float | None,
    body_max_tokens: int | None,
    agent_id: str | None,
):
    """Resolve generation params from agent config or request body."""
    if agent_id:
        try:
            agent_uid = UUID(agent_id)
        except ValueError:
            return {}
        agent = services.agent_store.get_by_id(agent_uid)
        if agent:
            return {
                "temperature": (
                    body_temperature
                    if body_temperature is not None
                    else agent.temperature
                ),
                "top_p": (
                    body_top_p if body_top_p is not None else agent.top_p
                ),
                "max_tokens": (
                    body_max_tokens
                    if body_max_tokens is not None
                    else agent.max_tokens
                ),
            }
    return {
        "temperature": body_temperature,
        "top_p": body_top_p,
        "max_tokens": body_max_tokens,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tree_out(tree, num_chapters: int) -> KnowledgeTreeOut:
    return KnowledgeTreeOut(
        id=str(tree.id),
        title=tree.title,
        description=tree.description,
        num_chapters=num_chapters,
        created_at=tree.created_at.isoformat(),
    )


def _chapter_out(ch) -> KnowledgeChapterOut:
    return KnowledgeChapterOut(
        id=str(ch.id),
        tree_id=str(ch.tree_id),
        number=ch.number,
        title=ch.title,
        created_at=ch.created_at.isoformat(),
    )


def _doc_out(doc) -> KnowledgeDocumentOut:
    return KnowledgeDocumentOut(
        id=str(doc.id),
        tree_id=str(doc.tree_id),
        chapter_id=str(doc.chapter_id) if doc.chapter_id else None,
        chapter_number=doc.chapter_number,
        title=doc.title,
        content=doc.content,
        is_main=doc.is_main,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        source_file_path=doc.source_file_path,
        source_file_name=doc.source_file_name,
        page_start=doc.page_start,
        page_end=doc.page_end,
    )


def _parse_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid {label}: {value}")


def _set_progress(task: Task, pct: int, message: str) -> None:
    task.progress_pct = max(0, min(100, pct))
    task.progress = message
    logger.debug("Progress [%d%%]: %s", task.progress_pct, message)


def _preview_file(
    tmp_path: Path, suffix: str, file_bytes: bytes, epub_config
) -> "DocumentPreviewOut | None":
    """Preview a PDF or EPUB file and return chapter structure."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    if suffix == ".pdf":
        doc, chapters = preview_pdf(tmp_path, file_hash)
    elif suffix == ".epub":
        doc, chapters = preview_epub(tmp_path, file_hash, epub_config)
    else:
        return None
    if doc is None:
        return None
    return DocumentPreviewOut(
        file_hash=doc.file_hash,
        filename=doc.original_filename,
        num_chapters=len(chapters),
        chapters=[
            ChapterPreviewOut(
                index=c.index,
                title=c.title,
                page_start=c.page_start,
                page_end=c.page_end,
            )
            for c in chapters
        ],
    )


# ---------------------------------------------------------------------------
# Trees
# ---------------------------------------------------------------------------


@router.get("/knowledge-trees", response_model=list[KnowledgeTreeOut])
async def list_trees(
    current_user: CurrentUser,
    services: ServicesDep
) -> list[KnowledgeTreeOut]:
    """List user's knowledge trees."""
    trees = services.kt_tree_store.list_trees_for_user(current_user.id)
    result = []
    for tree in trees:
        chapters = services.kt_chapter_store.list_chapters(tree.id)
        result.append(_tree_out(tree, len(chapters)))
    return result


@router.post("/knowledge-trees", response_model=KnowledgeTreeOut, status_code=201)
async def create_tree(
    req: CreateTreeRequest,
    current_user: CurrentUser,
    services: ServicesDep
) -> KnowledgeTreeOut:
    """Create a new knowledge tree."""
    limits = services.subscription_store.get_user_limits(current_user.id)
    check_can_create_tree(limits)

    tree = services.kt_tree_store.create_tree(req.title, req.description, current_user.id)
    return _tree_out(tree, 0)


@router.post("/knowledge-trees/preview", response_model=DocumentPreviewOut)
async def preview_tree_document(
    services: ServicesDep,
    file: UploadFile = File(...),
) -> DocumentPreviewOut:
    """Preview chapter structure of a PDF or EPUB without creating a tree."""
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".epub"):
        raise HTTPException(status_code=422, detail="Only PDF and EPUB files are supported")

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        preview = _preview_file(tmp_path, suffix, content, services.config.epub)
        if preview is None:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type or failed to parse document",
            )
        return preview
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/knowledge-trees/import", status_code=202)
async def import_tree_from_document(
    current_user: CurrentUser,
    services: ServicesDep,
    file: UploadFile = File(...),
    title: str = Form(""),
    chapter_indices: str | None = Form(None),
) -> dict:
    """Create a knowledge tree from a PDF or EPUB, auto-creating chapters.

    Optionally pass ``chapter_indices`` as a comma-separated string of 0-based
    integers to import only those chapters (e.g. ``"0,2,3"``).  Omit the field
    to import all chapters (default behaviour).
    """
    # Check tree limit first
    limits = services.subscription_store.get_user_limits(current_user.id)
    check_can_create_tree(limits)

    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".epub"):
        raise HTTPException(status_code=422, detail="Only PDF and EPUB files are supported")

    parsed_indices: list[int] | None = None
    if chapter_indices is not None:
        tokens = [t.strip() for t in chapter_indices.split(",") if t.strip()]
        try:
            parsed_indices = [int(t) for t in tokens]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="chapter_indices must be a comma-separated list of integers",
            )
        if not parsed_indices:
            raise HTTPException(
                status_code=400,
                detail="chapter_indices must contain at least one chapter",
            )

    tree_title = title.strip() or Path(filename).stem
    file_bytes = await file.read()
    task_id = services.task_registry.submit(
        _create_tree_from_document_background,
        file_bytes,
        filename,
        tree_title,
        services,
        parsed_indices,
        current_user.id,  # Pass user_id to background task
        task_type="kt_create_from_file",
        filename=filename,
    )
    return {"task_id": task_id, "filename": filename}


def _create_tree_from_document_background(
    task: Task,
    file_bytes: bytes,
    filename: str,
    tree_title: str,
    services: ServicesDep,
    chapter_indices: list[int] | None = None,
    user_id: UUID = None,
) -> dict:
    """Background task: parse file, create tree with chapters and knowledge documents.

    Args:
        chapter_indices: 0-based indices of chapters to import.  ``None`` means
            all chapters (default behaviour).
    """
    t0 = time.perf_counter()
    try:
        _set_progress(task, 5, "Saving uploaded file...")
        suffix = Path(filename).suffix.lower()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            _set_progress(task, 10, "Parsing document...")
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            if suffix == ".pdf":
                from infrastructure.ingest.pdf_loader import load_pdf as _load_pdf

                doc = _load_pdf(tmp_path, file_hash, filename)
            elif suffix in (".epub",):
                from infrastructure.ingest.epub_loader import load_epub as _load_epub

                doc = _load_epub(tmp_path, file_hash, filename)
            else:
                raise ValueError(f"Unsupported file type: {suffix}")

            _set_progress(task, 20, "Creating knowledge tree...")

            # Check document limits before creating
            if chapter_indices is not None:
                selected = set(chapter_indices)
                chapters_to_process = [ch for ch in doc.chapters if ch.index in selected]
            else:
                chapters_to_process = doc.chapters

            limits = services.subscription_store.get_user_limits(user_id)
            num_new_docs = len(chapters_to_process)

            if limits.current_documents + num_new_docs > limits.max_documents:
                raise PlanLimitExceeded(
                    resource="document",
                    current=limits.current_documents,
                    max_limit=limits.max_documents,
                    message=(
                        f"This import would create {num_new_docs} documents, "
                        f"exceeding your limit of {limits.max_documents}."
                    ),
                )

            tree = services.kt_tree_store.create_tree(tree_title, None, user_id)
            tree_uid = tree.id
            storage_dir = PROJECT_ROOT / "data" / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            tree_file_path = storage_dir / f"{tree_uid}{suffix}"
            tree_file_path.write_bytes(file_bytes)

            # Create a tree-level source document pointing to the full original file
            source_doc = services.kt_doc_store.create_document(
                tree_uid, None, doc.title or tree_title, "", is_main=False,
            )
            services.kt_doc_store.update_document_source_file(
                source_doc.id, str(tree_file_path), filename
            )

            chapter_count = len(chapters_to_process)
            if chapter_count == 0:
                _set_progress(task, 100, "Done (no chapters found)")
                return {"tree_id": str(tree_uid), "chapter_count": 0}

            from core.model.document import Document as _Document

            splitter = ChapterAwareSplitter()
            all_kt_chunks = []

            for i, chapter in enumerate(chapters_to_process):
                chapter_number = i + 1  # 1-based
                pct_base = 25 + int(70 * i / chapter_count)
                chapter_title = chapter.title or f"Chapter {chapter_number}"
                _set_progress(
                    task,
                    pct_base,
                    f"Processing chapter {chapter_number}/{chapter_count}: {chapter_title}...",
                )

                # Create knowledge chapter
                kt_chapter = services.kt_chapter_store.create_chapter(tree_uid, chapter_title)
                chapter_uid = kt_chapter.id

                # Build a single-chapter Document for chunking
                single_chapter_doc = _Document(
                    source_path=doc.source_path,
                    title=doc.title,
                    file_hash=file_hash,
                    original_filename=filename,
                    chapters=[chapter],
                )

                chunks = splitter.split(single_chapter_doc)

                # Full chapter text for the knowledge document
                if chunks:
                    full_text = "\n\n".join(c.text for c in chunks)
                else:
                    # Fallback: concatenate page text directly
                    full_text = "\n\n".join(p.text for p in chapter.pages)

                # Derive page range from the chapter's page list
                ch_page_start = chapter.pages[0].number if chapter.pages else None
                ch_page_end = chapter.pages[-1].number if chapter.pages else None

                # Store one KnowledgeDocument per chapter
                kt_doc = services.kt_doc_store.create_document(
                    tree_uid, chapter_uid, chapter_title, full_text, is_main=False,
                    page_start=ch_page_start,
                    page_end=ch_page_end,
                )
                doc_uid = kt_doc.id

                # For PDFs, extract only this chapter's pages into a separate file
                if suffix == ".pdf" and ch_page_start and ch_page_end:
                    src_pdf = fitz.open(str(tree_file_path))
                    chapter_pdf = fitz.open()
                    chapter_pdf.insert_pdf(
                        src_pdf,
                        from_page=ch_page_start - 1,
                        to_page=ch_page_end - 1,
                    )
                    chapter_file_path = storage_dir / f"{doc_uid}.pdf"
                    chapter_pdf.save(str(chapter_file_path))
                    chapter_pdf.close()
                    src_pdf.close()
                    services.kt_doc_store.update_document_source_file(
                        kt_doc.id, str(chapter_file_path), filename
                    )
                else:
                    services.kt_doc_store.update_document_source_file(
                        kt_doc.id, str(tree_file_path), filename
                    )

                # Build KnowledgeChunk records for this chapter
                for j, c in enumerate(chunks):
                    all_kt_chunks.append(
                        KnowledgeChunk(
                            id=UUID(c.id) if c.id else uuid4(),
                            tree_id=tree_uid,
                            chapter_id=chapter_uid,
                            doc_id=doc_uid,
                            chunk_index=j,
                            text=c.text,
                            token_count=c.token_count,
                        )
                    )

            _set_progress(task, 90, "Storing content chunks...")
            if all_kt_chunks:
                services.kt_content_store.save_chunks(all_kt_chunks)

            elapsed = time.perf_counter() - t0
            _set_progress(task, 100, "Done")
            logger.info(
                "Created knowledge tree %s from %s in %.1fs (%d chapters, %d chunks)",
                str(tree_uid),
                filename,
                elapsed,
                chapter_count,
                len(all_kt_chunks),
            )
            return {"tree_id": str(tree_uid), "chapter_count": chapter_count}
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as e:
        logger.error("Knowledge tree creation from file failed: %s", e)
        raise


@router.get("/knowledge-trees/{tree_id}", response_model=KnowledgeTreeOut)
async def get_tree(tree_id: str, services: ServicesDep) -> KnowledgeTreeOut:
    """Get a knowledge tree by ID."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    chapters = services.kt_chapter_store.list_chapters(uid)
    return _tree_out(tree, len(chapters))


@router.put("/knowledge-trees/{tree_id}", response_model=KnowledgeTreeOut)
async def update_tree(
    tree_id: str, req: UpdateTreeRequest, services: ServicesDep
) -> KnowledgeTreeOut:
    """Update a knowledge tree's title and description."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    updated = services.kt_tree_store.update_tree(uid, req.title, req.description)
    chapters = services.kt_chapter_store.list_chapters(uid)
    return _tree_out(updated, len(chapters))


@router.delete("/knowledge-trees/{tree_id}", status_code=204)
async def delete_tree(tree_id: str, services: ServicesDep) -> None:
    """Delete a knowledge tree (cascades to chapters, documents, content)."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    services.kt_tree_store.delete_tree(uid)


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


@router.get(
    "/knowledge-trees/{tree_id}/chapters",
    response_model=list[KnowledgeChapterOut],
)
async def list_chapters(tree_id: str, services: ServicesDep) -> list[KnowledgeChapterOut]:
    """List chapters for a knowledge tree."""
    uid = _parse_uuid(tree_id, "tree_id")
    chapters = services.kt_chapter_store.list_chapters(uid)
    return [_chapter_out(ch) for ch in chapters]


@router.post(
    "/knowledge-trees/{tree_id}/chapters",
    response_model=KnowledgeChapterOut,
    status_code=201,
)
async def create_chapter(
    tree_id: str, req: CreateChapterRequest, services: ServicesDep
) -> KnowledgeChapterOut:
    """Create a new chapter in a knowledge tree."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    chapter = services.kt_chapter_store.create_chapter(uid, req.title)
    return _chapter_out(chapter)


@router.put(
    "/knowledge-trees/{tree_id}/chapters/{number}",
    response_model=KnowledgeChapterOut,
)
async def update_chapter(
    tree_id: str, number: int, req: UpdateChapterRequest, services: ServicesDep
) -> KnowledgeChapterOut:
    """Update a chapter's title."""
    uid = _parse_uuid(tree_id, "tree_id")
    try:
        updated = services.kt_chapter_store.update_chapter(uid, number, req.title)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")
    return _chapter_out(updated)


@router.delete(
    "/knowledge-trees/{tree_id}/chapters/{number}",
    status_code=204,
)
async def delete_chapter(tree_id: str, number: int, services: ServicesDep) -> None:
    """Delete a chapter (1-based number) and its documents/content."""
    uid = _parse_uuid(tree_id, "tree_id")
    services.kt_chapter_store.delete_chapter(uid, number)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@router.get(
    "/knowledge-trees/{tree_id}/documents",
    response_model=list[KnowledgeDocumentOut],
)
async def list_documents(
    tree_id: str,
    services: ServicesDep,
    chapter_id: str | None = None,
) -> list[KnowledgeDocumentOut]:
    """List documents for a knowledge tree, optionally filtered by chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    chap_uid: UUID | None = None
    if chapter_id is not None:
        chap_uid = _parse_uuid(chapter_id, "chapter_id")
    docs = services.kt_doc_store.list_documents(uid, chap_uid)
    return [_doc_out(d) for d in docs]


@router.post(
    "/knowledge-trees/{tree_id}/documents",
    response_model=KnowledgeDocumentOut,
    status_code=201,
)
async def create_document(
    tree_id: str, req: CreateDocumentRequest, services: ServicesDep
) -> KnowledgeDocumentOut:
    """Create a new document in a knowledge tree."""
    uid = _parse_uuid(tree_id, "tree_id")
    chap_uid: UUID | None = None
    if req.chapter_id is not None:
        chap_uid = _parse_uuid(req.chapter_id, "chapter_id")
    doc = services.kt_doc_store.create_document(uid, chap_uid, req.title, req.content, req.is_main)
    return _doc_out(doc)


@router.put(
    "/knowledge-trees/{tree_id}/documents/{doc_id}",
    response_model=KnowledgeDocumentOut,
)
async def update_document(
    tree_id: str,
    doc_id: str,
    req: UpdateDocumentRequest,
    services: ServicesDep,
) -> KnowledgeDocumentOut:
    """Update title and content of a knowledge document."""
    doc_uid = _parse_uuid(doc_id, "doc_id")
    existing = services.kt_doc_store.get_document(doc_uid)
    if existing is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    updated = services.kt_doc_store.update_document(doc_uid, req.title, req.content)
    return _doc_out(updated)


@router.delete(
    "/knowledge-trees/{tree_id}/documents/{doc_id}",
    status_code=204,
)
async def delete_document(tree_id: str, doc_id: str, services: ServicesDep) -> None:
    """Delete a knowledge document."""
    doc_uid = _parse_uuid(doc_id, "doc_id")
    services.kt_doc_store.delete_document(doc_uid)


@router.get("/knowledge-trees/{tree_id}/documents/{doc_id}/file")
async def get_document_file(tree_id: str, doc_id: str, services: ServicesDep):
    uid = _parse_uuid(tree_id, "tree_id")
    doc_uid = _parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != uid or not doc.source_file_path:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(doc.source_file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    media_type = "application/pdf" if path.suffix == ".pdf" else "application/epub+zip"
    return FileResponse(path, filename=doc.source_file_name or path.name, media_type=media_type)


@router.get("/knowledge-trees/{tree_id}/documents/{doc_id}/thumbnail")
async def get_document_thumbnail(tree_id: str, doc_id: str, services: ServicesDep):
    """Return a PNG thumbnail of the first page of a PDF document."""
    uid = _parse_uuid(tree_id, "tree_id")
    doc_uid = _parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != uid or not doc.source_file_path:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(doc.source_file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    if path.suffix != ".pdf":
        raise HTTPException(status_code=404, detail="Thumbnails only available for PDF files")
    pdf = fitz.open(str(path))
    try:
        page = pdf[0]
        pix = page.get_pixmap(dpi=72)
        img_bytes = pix.tobytes("png")
    finally:
        pdf.close()
    return Response(content=img_bytes, media_type="image/png")


# ---------------------------------------------------------------------------
# File ingest into a chapter
# ---------------------------------------------------------------------------


def _ingest_file_background(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    file_bytes: bytes,
    filename: str,
    services: ServicesDep,
) -> dict:
    """Background task: parse file, chunk text, store as knowledge document."""
    t0 = time.perf_counter()
    try:
        _set_progress(task, 5, "Saving uploaded file...")
        suffix = Path(filename).suffix.lower()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            _set_progress(task, 15, "Parsing document...")
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            if suffix == ".pdf":
                from infrastructure.ingest.pdf_loader import load_pdf as _load_pdf

                doc = _load_pdf(tmp_path, file_hash, filename)
            elif suffix == ".epub":
                from infrastructure.ingest.epub_loader import load_epub as _load_epub

                doc = _load_epub(tmp_path, file_hash, filename)
            elif suffix == ".txt":
                from infrastructure.ingest.txt_loader import load_txt as _load_txt

                doc = _load_txt(tmp_path, file_hash, filename)
                if doc is None:
                    raise ValueError(f"No text could be extracted from '{filename}'.")
            else:
                raise ValueError(f"Unsupported file type: {suffix}")

            _set_progress(task, 40, "Chunking document...")
            splitter = ChapterAwareSplitter()
            chunks = splitter.split(doc)

            # Combine all chunks into a single text for the knowledge document
            full_text = "\n\n".join(c.text for c in chunks)

            if not full_text.strip():
                raise ValueError(
                    f"No text could be extracted from '{filename}'. "
                    "The file may be a scanned image, password-protected, or corrupt."
                )

            title = Path(filename).stem

            _set_progress(task, 60, "Storing document...")
            kt_doc = services.kt_doc_store.create_document(
                tree_id, chapter_id, title, full_text, is_main=False
            )
            doc_uid = kt_doc.id
            storage_dir = PROJECT_ROOT / "data" / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            file_path = storage_dir / f"{doc_uid}{suffix}"
            file_path.write_bytes(file_bytes)
            services.kt_doc_store.update_document_source_file(doc_uid, str(file_path), filename)

            _set_progress(task, 75, "Storing content chunks...")
            kt_chunks = [
                KnowledgeChunk(
                    id=UUID(c.id) if c.id else uuid4(),
                    tree_id=tree_id,
                    chapter_id=chapter_id,
                    doc_id=doc_uid,
                    chunk_index=i,
                    text=c.text,
                    token_count=c.token_count,
                )
                for i, c in enumerate(chunks)
            ]
            services.kt_content_store.save_chunks(kt_chunks)

            elapsed = time.perf_counter() - t0
            _set_progress(task, 100, "Done")
            logger.info(
                "Ingested knowledge file %s in %.1fs (%d chunks)",
                filename,
                elapsed,
                len(kt_chunks),
            )
            return {
                "doc_id": str(doc_uid),
                "title": title,
                "chunks": len(kt_chunks),
            }
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as e:
        logger.error("Knowledge file ingest failed: %s", e)
        raise


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/documents/ingest",
    status_code=202,
)
async def ingest_document(
    tree_id: str,
    number: int,
    services: ServicesDep,
    file: UploadFile = File(...),
) -> dict:
    """Ingest a PDF or EPUB file into a knowledge tree chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    chapters = services.kt_chapter_store.list_chapters(uid)
    chapter = next((c for c in chapters if c.number == number), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")

    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".epub", ".txt"):
        raise HTTPException(status_code=422, detail="Only PDF, EPUB, and TXT files are supported")

    file_bytes = await file.read()
    task_id = services.task_registry.submit(
        _ingest_file_background,
        uid,
        chapter.id,
        number,
        file_bytes,
        filename,
        services,
        task_type="kt_ingest",
    )
    return {"task_id": task_id, "filename": filename}


# ---------------------------------------------------------------------------
# Get chunks for a chapter
# ---------------------------------------------------------------------------


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/content",
    response_model=list[KnowledgeChunkOut],
)
async def get_chapter_content(
    tree_id: str, number: int, services: ServicesDep
) -> list[KnowledgeChunkOut]:
    """Get raw content chunks for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    kt_chunks = services.kt_content_store.get_chunks(uid, number)
    return [
        KnowledgeChunkOut(
            id=str(kc.id),
            chunk_index=kc.chunk_index,
            text=kc.text,
            token_count=kc.token_count,
        )
        for kc in kt_chunks
    ]


# ---------------------------------------------------------------------------
# Questions for a chapter
# ---------------------------------------------------------------------------


def _questions_background(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    services: ServicesDep,
    requested_types: list[QuestionType] | None,
    model: str | None = None,
    agent_id: str | None = None,
    num_questions: int | None = None,
) -> dict:
    """Background task: generate questions for a knowledge chapter."""
    t0 = time.perf_counter()
    try:
        _set_progress(task, 5, f"Retrieving chunks for chapter {chapter_number}...")
        kt_chunks = services.kt_content_store.get_chunks(tree_id, chapter_number)
        if not kt_chunks:
            raise ValueError(f"No content found for chapter {chapter_number}")

        chunks = [
            Chunk(
                text=kc.text,
                token_count=kc.token_count,
                metadata=ChunkMetadata(
                    source_file=str(kc.tree_id),
                    chapter_index=chapter_number - 1,
                    page_number=0,
                    start_char=0,
                    end_char=0,
                ),
            )
            for kc in kt_chunks
        ]

        _set_progress(task, 15, "Starting question generation...")
        llm, agent_prompt = _resolve_agent_llm(services, model, agent_id, services.fast_llm)
        agent = QuestionGeneratorAgent(llm)

        # Divide progress range 20-85 evenly across requested types
        types_to_generate: list[QuestionType] = requested_types or [
            "true_false",
            "multiple_choice",
            "matching",
            "checkbox",
        ]
        num_types = len(types_to_generate)
        progress_per_type = (85 - 20) // num_types if num_types > 0 else 65

        # Track progress per type using a mutable container
        type_progress_base = [20]

        def on_progress(qtype: QuestionType, batch_i: int, total_batches: int) -> None:
            base = type_progress_base[0]
            within = int((batch_i / total_batches) * progress_per_type) if total_batches > 0 else 0
            _set_progress(
                task,
                base + within,
                f"Generating {qtype.replace('_', ' ')} questions... "
                f"batch {batch_i}/{total_batches}",
            )

        all_questions: list[Question] = []
        counts: dict[str, int] = {}

        for i, qtype in enumerate(types_to_generate):
            type_progress_base[0] = 20 + i * progress_per_type
            _set_progress(
                task,
                type_progress_base[0],
                f"Generating {qtype.replace('_', ' ')} questions...",
            )

            result = agent.generate(
                chunks,
                question_types=[qtype],
                on_progress=on_progress,
                num_questions=num_questions,
                agent_prompt=agent_prompt or None,
            )
            items = result.get(qtype, [])

            for item in items:
                all_questions.append(
                    Question(
                        tree_id=tree_id,
                        chapter_id=chapter_id,
                        question_type=qtype,
                        question_data=item,
                    )
                )
            counts[qtype] = len(items)

        _set_progress(task, 90, f"Saving {len(all_questions)} questions...")
        if all_questions:
            services.kt_question_store.save_questions(all_questions)

        _set_progress(task, 100, "Done")
        elapsed = time.perf_counter() - t0
        logger.info(
            "Generated questions for knowledge chapter %d in %.1fs: %s",
            chapter_number,
            elapsed,
            counts,
        )
        return {"chapter": chapter_number, "counts": counts}
    except Exception as e:
        logger.error("Knowledge question generation failed: %s", e)
        raise


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/questions",
    status_code=202,
)
async def generate_questions(
    tree_id: str,
    number: int,
    services: ServicesDep,
    req: GenerateQuestionsRequest | None = None,
) -> dict:
    """Start background question generation for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    chapters = services.kt_chapter_store.list_chapters(uid)
    chapter = next((c for c in chapters if c.number == number), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")

    requested_types = req.question_types if req else None
    model = req.model if req else None
    agent_id = req.agent_id if req else None
    num_questions = req.num_questions if req else None

    task_id = services.task_registry.submit(
        _questions_background,
        uid,
        chapter.id,
        number,
        services,
        requested_types,
        model,
        agent_id,
        num_questions,
        task_type="kt_questions",
    )
    return {"task_id": task_id, "task_type": "kt_questions"}


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/questions",
    response_model=list[QuestionOut],
)
async def get_chapter_questions(
    tree_id: str,
    number: int,
    services: ServicesDep,
    type: QuestionType | None = None,
) -> list[QuestionOut]:
    """Get stored questions for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    chapters = services.kt_chapter_store.list_chapters(uid)
    chapter = next((c for c in chapters if c.number == number), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")

    questions = services.kt_question_store.get_questions(uid, chapter.id, question_type=type)
    return [
        QuestionOut(
            id=q.id,
            question_type=q.question_type,
            question_data=q.question_data,
            created_at=q.created_at,
        )
        for q in questions
    ]


@router.delete(
    "/knowledge-trees/{tree_id}/chapters/{number}/questions/{question_id}",
    status_code=204,
)
async def delete_question(
    tree_id: str,
    number: int,
    question_id: str,
    services: ServicesDep,
) -> None:
    """Delete a single question by ID."""
    q_uid = _parse_uuid(question_id, "question_id")
    services.kt_question_store.delete_question(q_uid)


@router.delete(
    "/knowledge-trees/{tree_id}/chapters/{number}/questions",
    status_code=204,
)
async def delete_all_questions(
    tree_id: str,
    number: int,
    services: ServicesDep,
    type: str | None = None,
) -> None:
    """Delete all questions for a chapter, optionally filtered by type."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    services.kt_question_store.delete_all_questions(uid, chapter.id, question_type=type)


# ---------------------------------------------------------------------------
# Exam sessions
# ---------------------------------------------------------------------------


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/exam-sessions",
    response_model=ExamSessionOut,
    status_code=201,
)
async def save_exam_session(
    tree_id: str,
    number: int,
    req: CreateExamSessionRequest,
    services: ServicesDep,
) -> ExamSessionOut:
    """Save the results of an exam session for a knowledge chapter."""
    uid, chapter = _resolve_chapter(services, tree_id, number)

    session = ExamSession(
        id=uuid4(),
        tree_id=uid,
        chapter_id=chapter.id,
        score=req.score,
        total_questions=req.total_questions,
        correct_count=req.correct_count,
        question_ids=req.question_ids,
        results=req.results,
        created_at=datetime.now(),
    )
    saved = services.kt_exam_store.save_session(session)
    return ExamSessionOut(
        id=str(saved.id),
        tree_id=str(saved.tree_id),
        chapter_id=str(saved.chapter_id),
        score=saved.score,
        total_questions=saved.total_questions,
        correct_count=saved.correct_count,
        question_ids=saved.question_ids,
        results=saved.results,
        created_at=saved.created_at.isoformat(),
    )


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/exam-sessions",
    response_model=list[ExamSessionOut],
)
async def list_exam_sessions(
    tree_id: str,
    number: int,
    services: ServicesDep,
) -> list[ExamSessionOut]:
    """List exam sessions for a knowledge chapter, newest first."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    sessions = services.kt_exam_store.list_sessions(uid, chapter.id)
    return [
        ExamSessionOut(
            id=str(s.id),
            tree_id=str(s.tree_id),
            chapter_id=str(s.chapter_id),
            score=s.score,
            total_questions=s.total_questions,
            correct_count=s.correct_count,
            question_ids=s.question_ids,
            results=s.results,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/exam-sessions/{session_id}",
    response_model=ExamSessionOut,
)
async def get_exam_session(
    tree_id: str,
    number: int,
    session_id: str,
    services: ServicesDep,
) -> ExamSessionOut:
    """Get a single exam session by ID."""
    sid = _parse_uuid(session_id, "session_id")
    session = services.kt_exam_store.get_session(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Exam session not found")
    return ExamSessionOut(
        id=str(session.id),
        tree_id=str(session.tree_id),
        chapter_id=str(session.chapter_id),
        score=session.score,
        total_questions=session.total_questions,
        correct_count=session.correct_count,
        question_ids=session.question_ids,
        results=session.results,
        created_at=session.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Flashcards for a chapter
# ---------------------------------------------------------------------------


class GenerateFlashcardRequest(BaseModel):
    selected_text: str


def _flashcard_background(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    _chapter_number: int,
    selected_text: str,
    services: ServicesDep,
) -> dict:
    try:
        _set_progress(task, 10, "Generating flashcard...")
        agent = FlashcardGeneratorAgent(services.llm)
        flashcard = agent.create_flashcard(
            selected_text=selected_text,
            tree_id=str(tree_id),
            chapter_id=str(chapter_id),
        )
        _set_progress(task, 70, "Saving flashcard...")
        services.kt_flashcard_store.save_flashcard(flashcard)
        _set_progress(task, 100, "Done")
        return {"flashcard_id": str(flashcard.id)}
    except Exception as e:
        logger.error("Flashcard generation failed: %s", e)
        raise


@router.get("/knowledge-trees/{tree_id}/chapters/{number}/flashcards")
async def list_flashcards(
    tree_id: str, number: int, services: ServicesDep
) -> list[dict]:
    """List saved flashcards for a chapter."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    cards = services.kt_flashcard_store.list_flashcards(uid, chapter.id)
    return [
        {
            "id": str(c.id),
            "front": c.front,
            "back": c.back,
            "source_text": c.source_text,
            "created_at": c.created_at.isoformat(),
        }
        for c in cards
    ]


@router.delete("/knowledge-trees/{tree_id}/chapters/{number}/flashcards", status_code=204)
async def delete_all_flashcards(
    tree_id: str, number: int, services: ServicesDep
) -> None:
    """Delete all flashcards for a chapter."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    services.kt_flashcard_store.delete_all_flashcards(uid, chapter.id)


@router.delete(
    "/knowledge-trees/{tree_id}/chapters/{number}/flashcards/{flashcard_id}",
    status_code=204,
)
async def delete_flashcard(
    tree_id: str, number: int, flashcard_id: str, services: ServicesDep
) -> None:
    """Delete a single flashcard by ID."""
    f_uid = _parse_uuid(flashcard_id, "flashcard_id")
    services.kt_flashcard_store.delete_flashcard(f_uid)


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/flashcards", status_code=202)
async def generate_flashcard(
    tree_id: str, number: int, req: GenerateFlashcardRequest, services: ServicesDep
) -> dict:
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    chapters = services.kt_chapter_store.list_chapters(uid)
    chapter = next((c for c in chapters if c.number == number), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")
    task_id = services.task_registry.submit(
        _flashcard_background,
        uid,
        chapter.id,
        number,
        req.selected_text,
        services,
        task_type="kt_flashcard",
    )
    return {"task_id": task_id, "task_type": "kt_flashcard"}


# ---------------------------------------------------------------------------
# Bulk flashcard generation from chapter content
# ---------------------------------------------------------------------------


class GenerateFlashcardsRequest(BaseModel):
    num_flashcards: int | None = None
    model: str | None = None
    agent_id: str | None = None


def _flashcards_bulk_background(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    services: ServicesDep,
    num_flashcards: int | None = None,
    model: str | None = None,
    agent_id: str | None = None,
) -> dict:
    """Background task: generate multiple flashcards for a chapter from its chunks."""
    t0 = time.perf_counter()
    try:
        _set_progress(task, 5, f"Retrieving chunks for chapter {chapter_number}...")
        kt_chunks = services.kt_content_store.get_chunks(tree_id, chapter_number)
        if not kt_chunks:
            raise ValueError(f"No content found for chapter {chapter_number}")

        chunks = [
            Chunk(
                text=kc.text,
                token_count=kc.token_count,
                metadata=ChunkMetadata(
                    source_file=str(kc.tree_id),
                    chapter_index=chapter_number - 1,
                    page_number=0,
                    start_char=0,
                    end_char=0,
                ),
            )
            for kc in kt_chunks
        ]

        _set_progress(task, 15, "Starting flashcard generation...")
        llm, agent_prompt = _resolve_agent_llm(services, model, agent_id, services.fast_llm)
        agent = FlashcardGeneratorAgent(llm)

        def on_progress(batch_i: int, total_batches: int) -> None:
            pct = 15 + int((batch_i / total_batches) * 75) if total_batches > 0 else 90
            _set_progress(task, pct, f"Generating flashcards... batch {batch_i}/{total_batches}")

        flashcards = agent.generate_batch(
            chunks,
            tree_id=tree_id,
            chapter_id=chapter_id,
            num_flashcards=num_flashcards,
            agent_prompt=agent_prompt or None,
            on_progress=on_progress,
        )

        _set_progress(task, 90, f"Saving {len(flashcards)} flashcards...")
        for card in flashcards:
            services.kt_flashcard_store.save_flashcard(card)

        _set_progress(task, 100, "Done")
        elapsed = time.perf_counter() - t0
        logger.info(
            "Generated %d flashcards for chapter %d in %.1fs",
            len(flashcards), chapter_number, elapsed,
        )
        return {"count": len(flashcards)}
    except Exception as e:
        logger.error("Bulk flashcard generation failed: %s", e)
        raise


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/flashcards/generate",
    status_code=202,
)
async def generate_flashcards_bulk(
    tree_id: str,
    number: int,
    services: ServicesDep,
    req: GenerateFlashcardsRequest | None = None,
) -> dict:
    """Start background bulk flashcard generation from chapter chunks."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    num_flashcards = req.num_flashcards if req else None
    model = req.model if req else None
    agent_id = req.agent_id if req else None
    task_id = services.task_registry.submit(
        _flashcards_bulk_background,
        uid,
        chapter.id,
        number,
        services,
        num_flashcards,
        model,
        agent_id,
        task_type="kt_flashcards_bulk",
    )
    return {"task_id": task_id, "task_type": "kt_flashcards_bulk"}


# ---------------------------------------------------------------------------
# Draft / approve workflow for selection-based content
# ---------------------------------------------------------------------------


class DraftFlashcardRequest(BaseModel):
    selected_text: str
    model: str | None = None
    agent_id: str | None = None


class SaveFlashcardRequest(BaseModel):
    front: str
    back: str
    source_text: str | None = None


class DraftQuestionRequest(BaseModel):
    question_type: QuestionType
    selected_text: str
    model: str | None = None
    agent_id: str | None = None


class SaveQuestionRequest(BaseModel):
    question_type: QuestionType
    question_data: dict


def _resolve_chapter(services: ServicesDep, tree_id: str, number: int):
    uid = _parse_uuid(tree_id, "tree_id")
    if services.kt_tree_store.get_tree(uid) is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    chapter = next(
        (c for c in services.kt_chapter_store.list_chapters(uid) if c.number == number), None
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")
    return uid, chapter


def _chapter_context(
    services: ServicesDep,
    tree_id: UUID,
    number: int,
    selected_text: str = "",
    max_tokens: int = 4000,
) -> str:
    chunks = services.kt_content_store.get_chunks(tree_id, number)
    window = chunks_around_selection(chunks, selected_text, neighbors=1)
    joined = "\n\n".join(c.text for c in window if c.text)
    return truncate_tokens(joined, max_tokens)


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/flashcards/draft")
async def draft_flashcard(
    tree_id: str, number: int, req: DraftFlashcardRequest, services: ServicesDep
) -> dict:
    """Generate a flashcard from a selection synchronously without persisting."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    if not req.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text is required")
    context = _chapter_context(services, uid, number, selected_text=req.selected_text)
    llm, agent_prompt = _resolve_agent_llm(services, req.model, req.agent_id, services.fast_llm)
    agent = FlashcardGeneratorAgent(llm)
    try:
        data = agent.generate(
            req.selected_text,
            chapter_context=context,
            agent_prompt=agent_prompt or None,
        )
    except Exception as e:
        logger.error("Flashcard draft failed: %s", e)
        raise HTTPException(status_code=502, detail="Flashcard generation failed") from e
    return {"front": data["front"], "back": data["back"], "source_text": req.selected_text}


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/flashcards/save")
async def save_flashcard(
    tree_id: str, number: int, req: SaveFlashcardRequest, services: ServicesDep
) -> dict:
    """Persist a user-approved (possibly edited) flashcard."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    front = req.front.strip()
    back = req.back.strip()
    if not front or not back:
        raise HTTPException(status_code=400, detail="front and back are required")
    flashcard = Flashcard(
        id=uuid4(),
        tree_id=uid,
        chapter_id=chapter.id,
        doc_id=None,
        front=front,
        back=back,
        source_text=req.source_text,
        created_at=datetime.now(),
    )
    services.kt_flashcard_store.save_flashcard(flashcard)
    return {"id": str(flashcard.id)}


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/questions/draft")
async def draft_question(
    tree_id: str, number: int, req: DraftQuestionRequest, services: ServicesDep
) -> dict:
    """Generate a single question of the given type from a selection without persisting."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    if not req.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text is required")
    context = _chapter_context(services, uid, number, selected_text=req.selected_text)
    llm, agent_prompt = _resolve_agent_llm(services, req.model, req.agent_id, services.fast_llm)
    agent = QuestionGeneratorAgent(llm)
    try:
        question_data = agent.generate_one(
            req.question_type,
            req.selected_text,
            chapter_context=context,
            agent_prompt=agent_prompt or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.error("Question draft failed: %s", e)
        raise HTTPException(status_code=502, detail="Question generation failed") from e
    return {"question_type": req.question_type, "question_data": question_data}


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/questions/save")
async def save_question(
    tree_id: str, number: int, req: SaveQuestionRequest, services: ServicesDep
) -> dict:
    """Persist a user-approved (possibly edited) question."""
    uid, chapter = _resolve_chapter(services, tree_id, number)
    if not QuestionGeneratorAgent.validate(req.question_type, req.question_data):
        raise HTTPException(status_code=422, detail="Question data failed validation")
    question = Question(
        tree_id=uid,
        chapter_id=chapter.id,
        question_type=req.question_type,
        question_data=req.question_data,
    )
    services.kt_question_store.save_questions([question])
    return {"id": str(question.id)}
