"""Knowledge Tree endpoints."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import fitz  # PyMuPDF
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep
from api.limit_checks import check_can_create_document, check_can_create_tree
from api.schemas.knowledge_tree import (
    ChapterPreviewOut,
    CreateChapterRequest,
    CreateDocumentRequest,
    CreateExamSessionRequest,
    CreateStudySessionRequest,
    CreateTreeRequest,
    DocumentPreviewOut,
    ExamSessionOut,
    ImportYouTubeRequest,
    KnowledgeChapterOut,
    KnowledgeChunkOut,
    KnowledgeDocumentOut,
    KnowledgeTreeOut,
    SplitChapterRequest,
    SplitChapterResponse,
    StudySessionOut,
    UpdateChapterRequest,
    UpdateDocumentRequest,
    UpdateTreeRequest,
)
from api.schemas.question import GenerateQuestionsRequest, QuestionOut
from application.agents.flashcard_generator import FlashcardGeneratorAgent
from application.agents.question_generator import QuestionGeneratorAgent
from application.agents.text_improvement import TextImprovementAgent
from application.llm_resolver import resolve_llm_for_agent
from application.services.chapter_helpers import get_chapter_context, parse_uuid, resolve_chapter
from application.services.flashcard_generation import (
    generate_flashcard_task,
    generate_flashcards_bulk_task,
)
from application.services.question_generation import generate_questions_task
from application.services.tree_import import (
    create_tree_from_file_task,
    import_youtube_task,
    ingest_file_task,
    split_chapter_into_ranges,
)
from core.exceptions import ProviderNotConfigured
from core.model.knowledge_tree import ExamSession, Flashcard, StudySession
from core.model.question import Question, QuestionType
from infrastructure.config import PROJECT_ROOT
from infrastructure.ingest.epub_loader import preview_epub
from infrastructure.ingest.pdf_loader import preview_pdf
from infrastructure.ingest.txt_loader import preview_txt

logger = logging.getLogger("knowledge_trees")

router = APIRouter()


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
        status=ch.status,
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
        original_content=doc.original_content,
        is_main=doc.is_main,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        source_file_path=doc.source_file_path,
        source_file_name=doc.source_file_name,
        page_start=doc.page_start,
        page_end=doc.page_end,
        source_type=doc.source_type,
        source_url=doc.source_url,
        file_type=doc.file_type,
    )


def _preview_file(
    tmp_path: Path, suffix: str, file_bytes: bytes, epub_config
) -> "DocumentPreviewOut | None":
    """Preview a PDF, EPUB, or TXT file and return chapter structure."""
    import hashlib
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    if suffix == ".pdf":
        doc, chapters = preview_pdf(tmp_path, file_hash)
    elif suffix == ".epub":
        doc, chapters = preview_epub(tmp_path, file_hash, epub_config)
    elif suffix == ".txt":
        doc, chapters = preview_txt(tmp_path, file_hash)
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
    if suffix not in (".pdf", ".epub", ".txt"):
        raise HTTPException(status_code=422, detail="Only PDF, EPUB, and TXT files are supported")

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
    limits = services.subscription_store.get_user_limits(current_user.id)
    check_can_create_tree(limits)

    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".epub", ".txt"):
        raise HTTPException(status_code=422, detail="Only PDF, EPUB, and TXT files are supported")

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
        create_tree_from_file_task,
        file_bytes,
        filename,
        tree_title,
        services,
        parsed_indices,
        current_user.id,
        task_type="kt_create_from_file",
        filename=filename,
    )
    return {"task_id": task_id, "filename": filename}


@router.post("/knowledge-trees/{tree_id}/documents/import-youtube", status_code=202)
async def import_youtube_document(
    tree_id: str,
    req: ImportYouTubeRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> dict:
    """Import a YouTube video as a knowledge document via transcript extraction."""
    uid = parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None or tree.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    limits = services.subscription_store.get_user_limits(current_user.id)
    check_can_create_document(limits)

    chapter_uid: UUID | None = None
    chapter_number: int | None = None
    if req.chapter_id:
        chapter_uid = parse_uuid(req.chapter_id, "chapter_id")
        chapter = next(
            (c for c in services.kt_chapter_store.list_chapters(uid) if c.id == chapter_uid),
            None,
        )
        if chapter is None:
            raise HTTPException(status_code=404, detail="Chapter not found")
        chapter_number = chapter.number

    task_id = services.task_registry.submit(
        import_youtube_task,
        req.url,
        uid,
        chapter_uid,
        chapter_number,
        services,
        task_type="kt_import_youtube",
    )
    return {"task_id": task_id}


@router.get("/knowledge-trees/{tree_id}", response_model=KnowledgeTreeOut)
async def get_tree(tree_id: str, services: ServicesDep) -> KnowledgeTreeOut:
    """Get a knowledge tree by ID."""
    uid = parse_uuid(tree_id, "tree_id")
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
    uid = parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")
    updated = services.kt_tree_store.update_tree(uid, req.title, req.description)
    chapters = services.kt_chapter_store.list_chapters(uid)
    return _tree_out(updated, len(chapters))


@router.get("/knowledge-trees/{tree_id}/export")
async def export_tree(
    tree_id: str,
    current_user: CurrentUser,
    services: ServicesDep,
) -> StreamingResponse:
    """Export a knowledge tree as a downloadable zip archive."""
    from io import BytesIO

    from application.export.tree_exporter import export_tree as _export_tree
    from application.export.tree_exporter import slugify

    uid = parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None or tree.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    zip_bytes = _export_tree(uid, services)
    fname = f"{slugify(tree.title)}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.delete("/knowledge-trees/{tree_id}", status_code=204)
async def delete_tree(tree_id: str, services: ServicesDep) -> None:
    """Delete a knowledge tree (cascades to chapters, documents, content)."""
    uid = parse_uuid(tree_id, "tree_id")
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
    uid = parse_uuid(tree_id, "tree_id")
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
    uid = parse_uuid(tree_id, "tree_id")
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
    uid = parse_uuid(tree_id, "tree_id")
    try:
        updated = services.kt_chapter_store.update_chapter(uid, number, req.title)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Chapter {number} not found")
    return _chapter_out(updated)


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/mark-read",
    status_code=204,
)
async def mark_chapter_read(tree_id: str, number: int, services: ServicesDep) -> None:
    """Mark a chapter as read."""
    uid = parse_uuid(tree_id, "tree_id")
    services.kt_chapter_store.mark_chapter_read(uid, number)


@router.delete(
    "/knowledge-trees/{tree_id}/chapters/{number}",
    status_code=204,
)
async def delete_chapter(tree_id: str, number: int, services: ServicesDep) -> None:
    """Delete a chapter (1-based number) and its documents/content."""
    uid = parse_uuid(tree_id, "tree_id")
    services.kt_chapter_store.delete_chapter(uid, number)


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/split",
    response_model=SplitChapterResponse,
    status_code=201,
)
async def split_chapter(
    tree_id: str,
    number: int,
    req: SplitChapterRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> SplitChapterResponse:
    """Split a chapter into multiple chapters by page ranges."""
    uid = parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None or tree.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    try:
        result_chapters = split_chapter_into_ranges(
            tree_id=uid,
            chapter_number=number,
            chapters=req.chapters,
            services=services,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SplitChapterResponse(
        chapters=[_chapter_out(c) for c in result_chapters]
    )


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
    uid = parse_uuid(tree_id, "tree_id")
    chap_uid: UUID | None = None
    if chapter_id is not None:
        chap_uid = parse_uuid(chapter_id, "chapter_id")
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
    uid = parse_uuid(tree_id, "tree_id")
    chap_uid: UUID | None = None
    if req.chapter_id is not None:
        chap_uid = parse_uuid(req.chapter_id, "chapter_id")
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
    """Update title, content, and file_type of a knowledge document."""
    doc_uid = parse_uuid(doc_id, "doc_id")
    existing = services.kt_doc_store.get_document(doc_uid)
    if existing is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    updated = services.kt_doc_store.update_document(doc_uid, req.title, req.content, req.file_type)
    return _doc_out(updated)


@router.delete(
    "/knowledge-trees/{tree_id}/documents/{doc_id}",
    status_code=204,
)
async def delete_document(tree_id: str, doc_id: str, services: ServicesDep) -> None:
    """Delete a knowledge document."""
    doc_uid = parse_uuid(doc_id, "doc_id")
    services.kt_doc_store.delete_document(doc_uid)


class ImproveDocumentRequest(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    agent_id: str | None = None
    model: str | None = None


@router.post(
    "/knowledge-trees/{tree_id}/documents/{doc_id}/improve",
    response_model=KnowledgeDocumentOut,
)
async def improve_document(
    tree_id: str,
    doc_id: str,
    req: ImproveDocumentRequest,
    _user: CurrentUser,
    services: ServicesDep,
) -> KnowledgeDocumentOut:
    """Improve document text style, apply Markdown formatting, and save atomically."""
    uid = parse_uuid(tree_id, "tree_id")
    doc_uid = parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != uid:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    if not doc.content or not doc.content.strip():
        raise HTTPException(status_code=422, detail="Document has no content to improve")

    from core.ports.llm import GenerationParams

    agent_uid = None
    if req.agent_id:
        try:
            agent_uid = UUID(req.agent_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid agent_id")

    try:
        llm, agent_prompt, agent_params = resolve_llm_for_agent(
            _user.id,
            agent_uid,
            services,
            model_override=req.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotConfigured as e:
        raise HTTPException(
            status_code=412,
            detail=f"Provider not configured: {e.provider}. Add an API key in Settings.",
        )

    def _param(value: float | None, fallback: float | None) -> float | None:
        return value if value is not None else fallback

    params = GenerationParams(
        temperature=_param(req.temperature, getattr(agent_params, "temperature", None)),
        top_p=_param(req.top_p, getattr(agent_params, "top_p", None)),
        max_tokens=_param(req.max_tokens, getattr(agent_params, "max_tokens", None)),
    )
    agent = TextImprovementAgent(llm)
    improved = agent.improve(doc.content, params=params, agent_prompt=agent_prompt)
    updated = services.kt_doc_store.save_improvement(doc_uid, improved)
    return _doc_out(updated)


@router.post(
    "/knowledge-trees/{tree_id}/documents/{doc_id}/revert",
    response_model=KnowledgeDocumentOut,
)
async def revert_document(
    tree_id: str,
    doc_id: str,
    _user: CurrentUser,
    services: ServicesDep,
) -> KnowledgeDocumentOut:
    """Revert a document to its pre-improvement original content."""
    uid = parse_uuid(tree_id, "tree_id")
    doc_uid = parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != uid:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    if doc.original_content is None:
        raise HTTPException(status_code=422, detail="Document has no improvement to revert")
    updated = services.kt_doc_store.revert_improvement(doc_uid)
    return _doc_out(updated)


@router.get("/knowledge-trees/{tree_id}/documents/{doc_id}/file")
async def get_document_file(tree_id: str, doc_id: str, services: ServicesDep):
    uid = parse_uuid(tree_id, "tree_id")
    doc_uid = parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    _file_path = doc.source_file_path if doc else None
    logger.info("GET file tree=%s doc=%s source_file_path=%s", tree_id, doc_id, _file_path)
    if doc is None or doc.tree_id != uid or not doc.source_file_path:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(doc.source_file_path)
    logger.info("  stored_path=%s exists=%s", path, path.exists())
    if not path.exists():
        storage_dir = PROJECT_ROOT / "data" / "storage"
        alt = storage_dir / path.name
        logger.info("  fallback_path=%s exists=%s PROJECT_ROOT=%s", alt, alt.exists(), PROJECT_ROOT)
        if alt.exists():
            path = alt
        else:
            raise HTTPException(status_code=404, detail="File not found on disk")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix == ".epub":
        media_type = "application/epub+zip"
    else:
        media_type = "text/plain; charset=utf-8"
    logger.info("  serving file=%s size=%s", path, path.stat().st_size if path.exists() else "?")
    return FileResponse(
        path, filename=doc.source_file_name or path.name,
        media_type=media_type, content_disposition_type="inline",
    )


@router.get("/knowledge-trees/{tree_id}/documents/{doc_id}/images/{image_name:path}")
async def get_document_image(tree_id: str, doc_id: str, image_name: str, services: ServicesDep):
    """Serve an image extracted from an EPUB document."""
    uid = parse_uuid(tree_id, "tree_id")
    doc_uid = parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    if doc is None or doc.tree_id != uid:
        raise HTTPException(status_code=404, detail="Document not found")
    storage_dir = PROJECT_ROOT / "data" / "storage"
    img_path = storage_dir / str(doc_uid) / "images" / image_name
    if not img_path.exists() or not img_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    suffix = img_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    return FileResponse(img_path, media_type=media_type)


@router.get("/knowledge-trees/{tree_id}/documents/{doc_id}/thumbnail")
async def get_document_thumbnail(tree_id: str, doc_id: str, services: ServicesDep):
    """Return a PNG thumbnail of the first page of a PDF document."""
    uid = parse_uuid(tree_id, "tree_id")
    doc_uid = parse_uuid(doc_id, "doc_id")
    doc = services.kt_doc_store.get_document(doc_uid)
    src = doc.source_file_path if doc else None
    logger.info("GET thumbnail tree=%s doc=%s source_file_path=%s", tree_id, doc_id, src)
    if doc is None or doc.tree_id != uid or not doc.source_file_path:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(doc.source_file_path)
    logger.info("  stored_path=%s exists=%s", path, path.exists())
    if not path.exists():
        storage_dir = PROJECT_ROOT / "data" / "storage"
        alt = storage_dir / path.name
        logger.info("  fallback_path=%s exists=%s PROJECT_ROOT=%s", alt, alt.exists(), PROJECT_ROOT)
        if alt.exists():
            path = alt
        else:
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
    uid = parse_uuid(tree_id, "tree_id")
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
        ingest_file_task,
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
    uid = parse_uuid(tree_id, "tree_id")
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


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/questions",
    status_code=202,
)
async def generate_questions(
    tree_id: str,
    number: int,
    current_user: CurrentUser,
    services: ServicesDep,
    req: GenerateQuestionsRequest | None = None,
) -> dict:
    """Start background question generation for a knowledge chapter."""
    uid, chapter = resolve_chapter(services, tree_id, number)

    requested_types = req.question_types if req else None
    model = req.model if req else None
    agent_id = req.agent_id if req else None
    num_questions = req.num_questions if req else None

    task_id = services.task_registry.submit(
        generate_questions_task,
        uid,
        chapter.id,
        number,
        services,
        current_user.id,
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
    uid, chapter = resolve_chapter(services, tree_id, number)

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
    q_uid = parse_uuid(question_id, "question_id")
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
    uid, chapter = resolve_chapter(services, tree_id, number)
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
    uid, chapter = resolve_chapter(services, tree_id, number)

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
    uid, chapter = resolve_chapter(services, tree_id, number)
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
    sid = parse_uuid(session_id, "session_id")
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
# Study sessions
# ---------------------------------------------------------------------------


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/study-sessions",
    response_model=StudySessionOut,
    status_code=201,
)
async def save_study_session(
    tree_id: str,
    number: int,
    req: CreateStudySessionRequest,
    services: ServicesDep,
) -> StudySessionOut:
    """Save the results of a study session for a knowledge chapter."""
    uid, chapter = resolve_chapter(services, tree_id, number)

    session = StudySession(
        id=uuid4(),
        tree_id=uid,
        chapter_id=chapter.id,
        total_cards=req.total_cards,
        question_ids=req.question_ids,
        created_at=datetime.now(),
    )
    saved = services.kt_study_store.save_session(session)
    return StudySessionOut(
        id=str(saved.id),
        tree_id=str(saved.tree_id),
        chapter_id=str(saved.chapter_id),
        total_cards=saved.total_cards,
        question_ids=saved.question_ids,
        created_at=saved.created_at.isoformat(),
    )


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/study-sessions",
    response_model=list[StudySessionOut],
)
async def list_study_sessions(
    tree_id: str,
    number: int,
    services: ServicesDep,
) -> list[StudySessionOut]:
    """List study sessions for a knowledge chapter, newest first."""
    uid, chapter = resolve_chapter(services, tree_id, number)
    sessions = services.kt_study_store.list_sessions(uid, chapter.id)
    return [
        StudySessionOut(
            id=str(s.id),
            tree_id=str(s.tree_id),
            chapter_id=str(s.chapter_id),
            total_cards=s.total_cards,
            question_ids=s.question_ids,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/study-sessions/{session_id}",
    response_model=StudySessionOut,
)
async def get_study_session(
    tree_id: str,
    number: int,
    session_id: str,
    services: ServicesDep,
) -> StudySessionOut:
    """Get a single study session by ID."""
    sid = parse_uuid(session_id, "session_id")
    session = services.kt_study_store.get_session(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Study session not found")
    return StudySessionOut(
        id=str(session.id),
        tree_id=str(session.tree_id),
        chapter_id=str(session.chapter_id),
        total_cards=session.total_cards,
        question_ids=session.question_ids,
        created_at=session.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Flashcards for a chapter
# ---------------------------------------------------------------------------


class GenerateFlashcardRequest(BaseModel):
    selected_text: str


@router.get("/knowledge-trees/{tree_id}/chapters/{number}/flashcards")
async def list_flashcards(
    tree_id: str, number: int, services: ServicesDep
) -> list[dict]:
    """List saved flashcards for a chapter."""
    uid, chapter = resolve_chapter(services, tree_id, number)
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
    uid, chapter = resolve_chapter(services, tree_id, number)
    services.kt_flashcard_store.delete_all_flashcards(uid, chapter.id)


@router.delete(
    "/knowledge-trees/{tree_id}/chapters/{number}/flashcards/{flashcard_id}",
    status_code=204,
)
async def delete_flashcard(
    tree_id: str, number: int, flashcard_id: str, services: ServicesDep
) -> None:
    """Delete a single flashcard by ID."""
    f_uid = parse_uuid(flashcard_id, "flashcard_id")
    services.kt_flashcard_store.delete_flashcard(f_uid)


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/flashcards", status_code=202)
async def generate_flashcard(
    tree_id: str, number: int, req: GenerateFlashcardRequest, services: ServicesDep
) -> dict:
    uid, chapter = resolve_chapter(services, tree_id, number)
    task_id = services.task_registry.submit(
        generate_flashcard_task,
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


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/flashcards/generate",
    status_code=202,
)
async def generate_flashcards_bulk(
    tree_id: str,
    number: int,
    current_user: CurrentUser,
    services: ServicesDep,
    req: GenerateFlashcardsRequest | None = None,
) -> dict:
    """Start background bulk flashcard generation from chapter chunks."""
    uid, chapter = resolve_chapter(services, tree_id, number)
    num_flashcards = req.num_flashcards if req else None
    model = req.model if req else None
    agent_id = req.agent_id if req else None
    task_id = services.task_registry.submit(
        generate_flashcards_bulk_task,
        uid,
        chapter.id,
        number,
        services,
        current_user.id,
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


@router.post("/knowledge-trees/{tree_id}/chapters/{number}/flashcards/draft")
async def draft_flashcard(
    tree_id: str,
    number: int,
    req: DraftFlashcardRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> dict:
    """Generate a flashcard from a selection synchronously without persisting."""
    uid, chapter = resolve_chapter(services, tree_id, number)
    if not req.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text is required")
    context = get_chapter_context(services, uid, number, selected_text=req.selected_text)
    agent_uid = UUID(req.agent_id) if req.agent_id else None
    try:
        llm, agent_prompt, _ = resolve_llm_for_agent(
            current_user.id, agent_uid, services, model_override=req.model
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotConfigured as e:
        raise HTTPException(status_code=412, detail=f"Provider not configured: {e.provider}")
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
    uid, chapter = resolve_chapter(services, tree_id, number)
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
    tree_id: str,
    number: int,
    req: DraftQuestionRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> dict:
    """Generate a single question of the given type from a selection without persisting."""
    uid, chapter = resolve_chapter(services, tree_id, number)
    if not req.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text is required")
    context = get_chapter_context(services, uid, number, selected_text=req.selected_text)
    agent_uid = UUID(req.agent_id) if req.agent_id else None
    try:
        llm, agent_prompt, _ = resolve_llm_for_agent(
            current_user.id, agent_uid, services, model_override=req.model
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotConfigured as e:
        raise HTTPException(status_code=412, detail=f"Provider not configured: {e.provider}")
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
    uid, chapter = resolve_chapter(services, tree_id, number)
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
