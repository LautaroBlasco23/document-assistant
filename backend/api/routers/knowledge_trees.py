"""Knowledge Tree endpoints."""

import hashlib
import json
import logging
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.deps import ServicesDep
from api.schemas.knowledge_tree import (
    ChapterPreviewOut,
    CreateChapterRequest,
    CreateDocumentRequest,
    CreateTreeRequest,
    DocumentPreviewOut,
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
from application.agents.question_generator import QuestionGeneratorAgent
from core.model.chunk import Chunk, ChunkMetadata
from core.model.knowledge_tree import Flashcard, KnowledgeChunk
from core.model.question import Question, QuestionType
from infrastructure.chunking.splitter import ChapterAwareSplitter
from infrastructure.config import PROJECT_ROOT
from infrastructure.ingest.epub_loader import preview_epub
from infrastructure.ingest.pdf_loader import preview_pdf

logger = logging.getLogger(__name__)

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
async def list_trees(services: ServicesDep) -> list[KnowledgeTreeOut]:
    """List all knowledge trees."""
    trees = services.kt_tree_store.list_trees()
    result = []
    for tree in trees:
        chapters = services.kt_chapter_store.list_chapters(tree.id)
        result.append(_tree_out(tree, len(chapters)))
    return result


@router.post("/knowledge-trees", response_model=KnowledgeTreeOut, status_code=201)
async def create_tree(req: CreateTreeRequest, services: ServicesDep) -> KnowledgeTreeOut:
    """Create a new knowledge tree."""
    tree = services.kt_tree_store.create_tree(req.title, req.description)
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
            tree = services.kt_tree_store.create_tree(tree_title, None)
            tree_uid = tree.id
            storage_dir = PROJECT_ROOT / "data" / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            tree_file_path = storage_dir / f"{tree_uid}{suffix}"
            tree_file_path.write_bytes(file_bytes)

            if chapter_indices is not None:
                selected = set(chapter_indices)
                chapters_to_process = [ch for ch in doc.chapters if ch.index in selected]
            else:
                chapters_to_process = doc.chapters

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
                    import fitz as _fitz
                    src_pdf = _fitz.open(str(tree_file_path))
                    chapter_pdf = _fitz.open()
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
            elif suffix in (".epub",):
                from infrastructure.ingest.epub_loader import load_epub as _load_epub

                doc = _load_epub(tmp_path, file_hash, filename)
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
    if suffix not in (".pdf", ".epub"):
        raise HTTPException(status_code=422, detail="Only PDF and EPUB files are supported")

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
        agent = QuestionGeneratorAgent(services.fast_llm)

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

            result = agent.generate(chunks, question_types=[qtype], on_progress=on_progress)
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

    task_id = services.task_registry.submit(
        _questions_background,
        uid,
        chapter.id,
        number,
        services,
        requested_types,
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


# ---------------------------------------------------------------------------
# Flashcards for a chapter
# ---------------------------------------------------------------------------


class GenerateFlashcardRequest(BaseModel):
    selected_text: str


def _flashcard_background(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    selected_text: str,
    services: ServicesDep,
) -> dict:
    try:
        _set_progress(task, 10, "Generating flashcard...")
        system = (
            "You are an expert educator. Create exactly ONE high-quality flashcard "
            "from the excerpt provided by the user.\n\n"
            "Return ONLY a JSON object with exactly two keys:\n"
            '{"front": "...", "back": "..."}\n\n'
            "Rules:\n"
            "- Front should be a concise question or term.\n"
            "- Back should be a precise, complete answer in 1-2 sentences.\n"
            "- Do NOT add markdown code fences.\n"
            "- Do NOT add any text outside the JSON object."
        )
        raw = services.llm.chat(system, selected_text, format="json")
        _set_progress(task, 70, "Parsing flashcard...")
        text = raw.strip()
        m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        data = json.loads(text)
        front = str(data["front"]).strip()
        back = str(data["back"]).strip()
        flashcard = Flashcard(
            id=uuid4(),
            tree_id=tree_id,
            chapter_id=chapter_id,
            doc_id=None,
            front=front,
            back=back,
            source_text=selected_text,
            created_at=datetime.now(),
        )
        services.kt_flashcard_store.save_flashcard(flashcard)
        _set_progress(task, 100, "Done")
        return {"flashcard_id": str(flashcard.id)}
    except Exception as e:
        logger.error("Flashcard generation failed: %s", e)
        raise


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
