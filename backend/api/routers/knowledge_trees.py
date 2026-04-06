"""Knowledge Tree endpoints."""

import functools
import hashlib
import logging
import tempfile
import time
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.deps import ServicesDep
from api.schemas.documents import ChapterPreviewOut, DocumentPreviewOut
from api.schemas.knowledge_tree import (
    CreateChapterRequest,
    CreateDocumentRequest,
    CreateTreeRequest,
    KnowledgeChapterOut,
    KnowledgeChunkOut,
    KnowledgeDocumentOut,
    KnowledgeTreeOut,
    UpdateChapterRequest,
    UpdateDocumentRequest,
    UpdateTreeRequest,
)
from api.tasks import Task
from application.agents.flashcard_generator import FlashcardGeneratorAgent
from application.agents.summarizer import SummarizerAgent
from application.ingest import preview_file
from core.model.chunk import Chunk, ChunkMetadata
from core.model.document import Chapter
from core.model.generated_content import Flashcard, Summary
from core.model.knowledge_tree import KnowledgeChunk
from infrastructure.chunking.splitter import ChapterAwareSplitter
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
        title=doc.title,
        content=doc.content,
        is_main=doc.is_main,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
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
        raise HTTPException(
            status_code=422, detail="Only PDF and EPUB files are supported"
        )

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        preview = preview_file(
            tmp_path,
            {
                ".pdf": preview_pdf,
                ".epub": functools.partial(preview_epub, epub_config=services.config.epub),
            },
        )
        if preview is None:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type or failed to parse document",
            )
        return DocumentPreviewOut(
            file_hash=preview.file_hash,
            filename=preview.filename,
            num_chapters=len(preview.chapters),
            chapters=[
                ChapterPreviewOut(
                    index=c.index,
                    title=c.title,
                    page_start=c.page_start,
                    page_end=c.page_end,
                )
                for c in preview.chapters
            ],
        )
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
        raise HTTPException(
            status_code=422, detail="Only PDF and EPUB files are supported"
        )

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
                    task, pct_base,
                    f"Processing chapter {chapter_number}/{chapter_count}: {chapter_title}..."
                )

                # Create knowledge chapter
                kt_chapter = services.kt_chapter_store.create_chapter(
                    tree_uid, chapter_title
                )
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

                # Store one KnowledgeDocument per chapter
                kt_doc = services.kt_doc_store.create_document(
                    tree_uid, chapter_uid, chapter_title, full_text, is_main=False
                )
                doc_uid = kt_doc.id

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
async def list_chapters(
    tree_id: str, services: ServicesDep
) -> list[KnowledgeChapterOut]:
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
async def delete_chapter(
    tree_id: str, number: int, services: ServicesDep
) -> None:
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
    doc = services.kt_doc_store.create_document(
        uid, chap_uid, req.title, req.content, req.is_main
    )
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
async def delete_document(
    tree_id: str, doc_id: str, services: ServicesDep
) -> None:
    """Delete a knowledge document."""
    doc_uid = _parse_uuid(doc_id, "doc_id")
    services.kt_doc_store.delete_document(doc_uid)


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
            title = Path(filename).stem

            _set_progress(task, 60, "Storing document...")
            kt_doc = services.kt_doc_store.create_document(
                tree_id, chapter_id, title, full_text, is_main=False
            )

            _set_progress(task, 75, "Storing content chunks...")
            doc_uid = kt_doc.id
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
        raise HTTPException(
            status_code=422, detail="Only PDF and EPUB files are supported"
        )

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
# Summarize a chapter
# ---------------------------------------------------------------------------


def _summarize_background(
    task: Task,
    tree_id: UUID,
    chapter_number: int,
    services: ServicesDep,
) -> dict:
    """Background task: summarize all chunks in a knowledge chapter."""
    t0 = time.perf_counter()
    try:
        _set_progress(task, 10, f"Retrieving chunks for chapter {chapter_number}...")
        kt_chunks = services.kt_content_store.get_chunks(tree_id, chapter_number)
        if not kt_chunks:
            raise ValueError(f"No content found for chapter {chapter_number}")

        # Convert KnowledgeChunks to domain Chunk objects for the agent
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

        _set_progress(task, 25, "Generating summary...")
        chapter_obj = Chapter(index=chapter_number - 1, title=f"Chapter {chapter_number}", pages=[])

        def on_progress(phase: str) -> None:
            if phase == "calling_llm":
                _set_progress(task, 40, "LLM is generating summary...")

        result = SummarizerAgent(services.fast_llm).summarize(
            chapter_obj,
            chunks,
            on_progress=on_progress,
        )

        _set_progress(task, 85, "Saving summary...")
        # Store using tree_id as document_hash placeholder and chapter_index_kt for column
        # We use a synthetic document_hash derived from tree_id + chapter_number
        synthetic_hash = f"kt_{str(tree_id).replace('-', '')}_{chapter_number}"[:64]
        chapter_index_0based = chapter_number - 1
        services.content_store.save_summary(
            Summary(
                document_hash=synthetic_hash,
                chapter_index=chapter_index_0based,
                content=result["content"],
                description=result["description"],
                bullets=result["bullets"],
            )
        )

        _set_progress(task, 100, "Done")
        elapsed = time.perf_counter() - t0
        logger.info(
            "Summarized knowledge chapter %d in %.1fs", chapter_number, elapsed
        )
        return {
            "chapter": chapter_number,
            "description": result["description"],
            "bullets": result["bullets"],
        }
    except Exception as e:
        logger.error("Knowledge summarization failed: %s", e)
        raise


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/summarize",
    status_code=202,
)
async def summarize_chapter(
    tree_id: str, number: int, services: ServicesDep
) -> dict:
    """Start background summarization task for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    task_id = services.task_registry.submit(
        _summarize_background,
        uid,
        number,
        services,
        task_type="kt_summarize",
    )
    return {"task_id": task_id, "task_type": "kt_summarize"}


# ---------------------------------------------------------------------------
# Flashcards for a chapter
# ---------------------------------------------------------------------------


def _flashcards_background(
    task: Task,
    tree_id: UUID,
    chapter_number: int,
    services: ServicesDep,
) -> dict:
    """Background task: generate flashcards for a knowledge chapter."""
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

        _set_progress(task, 20, "Generating flashcards...")

        def on_progress(batch: int, total: int, cards_so_far: int) -> None:
            pct = 20 + int((batch / total) * 60)
            _set_progress(
                task, pct, f"Building flashcards... batch {batch}/{total} ({cards_so_far} cards)"
            )

        cards = FlashcardGeneratorAgent(services.fast_llm).generate(
            chunks,
            on_progress=on_progress,
            chapter_title=f"Chapter {chapter_number}",
        )

        _set_progress(task, 85, "Saving flashcards...")
        synthetic_hash = f"kt_{str(tree_id).replace('-', '')}_{chapter_number}"[:64]
        chapter_index_0based = chapter_number - 1
        flashcard_models = [
            Flashcard(
                document_hash=synthetic_hash,
                chapter_index=chapter_index_0based,
                front=card["front"],
                back=card["back"],
                source_page=card.get("source_page"),
                source_chunk_id="",
                source_text="",
                status="pending",
            )
            for card in cards
        ]
        services.content_store.save_flashcards(flashcard_models)

        _set_progress(task, 100, "Done")
        elapsed = time.perf_counter() - t0
        logger.info(
            "Generated %d flashcards for knowledge chapter %d in %.1fs",
            len(cards),
            chapter_number,
            elapsed,
        )
        return {"chapter": chapter_number, "count": len(cards)}
    except Exception as e:
        logger.error("Knowledge flashcard generation failed: %s", e)
        raise


@router.post(
    "/knowledge-trees/{tree_id}/chapters/{number}/flashcards",
    status_code=202,
)
async def generate_flashcards(
    tree_id: str, number: int, services: ServicesDep
) -> dict:
    """Start background flashcard generation for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    tree = services.kt_tree_store.get_tree(uid)
    if tree is None:
        raise HTTPException(status_code=404, detail="Knowledge tree not found")

    task_id = services.task_registry.submit(
        _flashcards_background,
        uid,
        number,
        services,
        task_type="kt_flashcards",
    )
    return {"task_id": task_id, "task_type": "kt_flashcards"}


# ---------------------------------------------------------------------------
# Get summaries / flashcards / chunks for a chapter
# ---------------------------------------------------------------------------


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/summaries",
)
async def get_chapter_summary(
    tree_id: str, number: int, services: ServicesDep
) -> dict:
    """Get stored summary for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    synthetic_hash = f"kt_{str(uid).replace('-', '')}_{number}"[:64]
    chapter_index_0based = number - 1
    summary = services.content_store.get_summary(synthetic_hash, chapter_index_0based)
    if summary is None:
        raise HTTPException(status_code=404, detail="No summary found for this chapter")
    return {
        "chapter": number,
        "content": summary.content,
        "description": summary.description,
        "bullets": summary.bullets,
    }


@router.get(
    "/knowledge-trees/{tree_id}/chapters/{number}/flashcards",
)
async def get_chapter_flashcards(
    tree_id: str, number: int, services: ServicesDep
) -> list[dict]:
    """Get stored flashcards for a knowledge chapter."""
    uid = _parse_uuid(tree_id, "tree_id")
    synthetic_hash = f"kt_{str(uid).replace('-', '')}_{number}"[:64]
    chapter_index_0based = number - 1
    flashcards = services.content_store.get_flashcards(
        synthetic_hash, chapter_index_0based, status=None
    )
    return [
        {
            "id": f.id,
            "front": f.front,
            "back": f.back,
            "status": f.status,
        }
        for f in flashcards
    ]


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
