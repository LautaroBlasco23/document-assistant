"""Document management endpoints."""

import functools
import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path

import fitz
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from api.deps import ServicesDep
from api.schemas.documents import (
    AppendContentRequest,
    AppendContentResponse,
    ChapterDeleteResponse,
    ChapterOut,
    ChapterPreviewOut,
    CreateDocumentRequest,
    CreateDocumentResponse,
    DocumentContentResponse,
    DocumentOut,
    DocumentPreviewOut,
    DocumentStructureOut,
    IngestTaskOut,
    MetadataRequest,
    MetadataResponse,
    UpdateContentRequest,
    UpdateContentResponse,
)
from api.tasks import Task
from application.delete_document import delete_document as _delete_document
from application.ingest import _hash_file, ingest_file, preview_file
from core.model.document_metadata import DocumentMetadata
from infrastructure.chunking.splitter import ChapterAwareSplitter
from infrastructure.config import PROJECT_ROOT
from infrastructure.file_persistence import get_persisted_file, persist_file
from infrastructure.ingest.epub_loader import load_epub, preview_epub
from infrastructure.ingest.pdf_loader import load_pdf, preview_pdf
from infrastructure.ingest.txt_loader import build_document_from_text, load_txt, preview_txt
from infrastructure.output.manifest import remove_chapter_from_manifest, write_manifest
from infrastructure.output.markdown_writer import _safe_name

logger = logging.getLogger(__name__)

router = APIRouter()

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def _list_documents() -> list[dict]:
    """Scan data/output for manifest.json files."""
    documents = []
    if not OUTPUT_DIR.exists():
        return documents

    for doc_dir in OUTPUT_DIR.iterdir():
        if not doc_dir.is_dir():
            continue
        manifest_file = doc_dir / "manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file) as f:
                    manifest = json.load(f)
                documents.append(manifest)
            except Exception as e:
                logger.warning(f"Failed to read manifest {manifest_file}: {e}")

    return documents


def _get_document_chapters(file_hash: str, services: ServicesDep) -> list[ChapterOut]:
    """Get chapter info for a document by querying PostgreSQL + manifest."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    chapters_from_manifest: dict[int, dict] = {}
    if doc_manifest and "chapters" in doc_manifest:
        for ch in doc_manifest["chapters"]:
            chapters_from_manifest[ch.get("index", 0)] = {
                "title": ch.get("title", ""),
                "sections": ch.get("sections", []),
                "toc_href": ch.get("toc_href", ""),
            }

    try:
        chapter_structure = services.content_store.get_chapter_structure(file_hash)
        return [
            ChapterOut(
                number=user_chapter_num,
                chapter_index=chapter_index,
                title=chapters_from_manifest.get(chapter_index, {}).get(
                    "title", f"Chapter {user_chapter_num}"
                ),
                num_chunks=chunk_count,
                sections=chapters_from_manifest.get(chapter_index, {}).get("sections", []),
                toc_href=chapters_from_manifest.get(chapter_index, {}).get("toc_href", ""),
            )
            for user_chapter_num, (chapter_index, chunk_count) in enumerate(
                chapter_structure, start=1
            )
        ]
    except Exception as e:
        logger.warning(f"Failed to get chapters for {file_hash}: {e}")
        return []


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(services: ServicesDep) -> list[DocumentOut]:
    """List all ingested documents."""
    documents = _list_documents()
    result = [
        DocumentOut(
            file_hash=doc["file_hash"],
            filename=doc.get("original_filename") or Path(doc["source_path"]).name,
            num_chapters=doc.get("num_chapters", 0),
        )
        for doc in documents
    ]
    logger.info("Listed %d documents", len(result))
    return result


@router.post("/documents/preview", response_model=DocumentPreviewOut)
async def preview_document(
    services: ServicesDep,
    file: UploadFile = File(...),
) -> DocumentPreviewOut:
    """Preview a document's chapter structure without storing it.

    Returns chapter metadata (titles, page ranges) so the user can select
    which chapters to process.
    """
    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        preview = preview_file(
            tmp_path,
            {
                ".pdf": preview_pdf,
                ".epub": functools.partial(preview_epub, epub_config=services.config.epub),
                ".txt": preview_txt,
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
        tmp_path.unlink()


@router.post("/documents/{file_hash}/ingest", response_model=IngestTaskOut)
async def ingest_document_chapters(
    file_hash: str,
    services: ServicesDep,
    file: UploadFile = File(...),
    chapter_indices: str = Form(...),
    document_type: str = Form(""),
    description: str = Form(""),
) -> IngestTaskOut:
    """Ingest a document with only the selected chapters.

    This is the second step of the two-phase upload:
    1. POST /documents/preview - get chapter structure
    2. POST /documents/{hash}/ingest - ingest selected chapters
    """
    import json

    content = await file.read()
    chapter_indices_list = json.loads(chapter_indices)

    task_id = services.task_registry.submit(
        _ingest_selected_chapters,
        content,
        file.filename,
        services,
        file_hash,
        set(chapter_indices_list),
        document_type,
        description,
        task_type="ingest",
        filename=file.filename,
    )
    logger.info(
        "Ingest selected chapters submitted: %s -> task %s (chapters=%s)",
        file.filename,
        task_id,
        chapter_indices_list,
    )

    return IngestTaskOut(task_id=task_id, filename=file.filename)


def _ingest_selected_chapters(
    task: Task,
    file_content: bytes,
    filename: str,
    services: ServicesDep,
    expected_hash: str,
    chapter_indices: set[int],
    document_type: str = "",
    description: str = "",
) -> str:
    """Background task to ingest only selected chapters from an uploaded file."""
    t0 = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)

        task.progress = f"Hashing {filename}"
        logger.info("Ingest selected: hashing %s", filename)
        file_hash = _hash_file(tmp_path)

        if file_hash != expected_hash:
            raise ValueError(
                f"File hash mismatch. Expected {expected_hash[:12]}, got {file_hash[:12]}. "
                "The uploaded file may have changed."
            )

        if services.content_store.has_file(file_hash):
            task.progress = "File already ingested"
            logger.info("Ingest selected: %s already ingested", filename)
            tmp_path.unlink()
            return f"File already ingested (hash {file_hash[:12]})"

        task.progress = f"Loading {filename}"
        logger.info("Ingest selected: loading %s", filename)
        doc = ingest_file(
            tmp_path,
            loaders={
                ".pdf": load_pdf,
                ".epub": functools.partial(load_epub, epub_config=services.config.epub),
                ".txt": load_txt,
            },
            original_filename=filename,
        )
        if doc is None:
            raise ValueError("Failed to load document")

        task.progress = "Chunking selected chapters..."
        logger.info("Ingest selected: chunking with %d chapter indices", len(chapter_indices))
        splitter = ChapterAwareSplitter(
            max_tokens=services.config.chunking.max_tokens,
            overlap_tokens=services.config.chunking.overlap_tokens,
        )
        chunks = splitter.split(doc, chapter_indices=chapter_indices)
        logger.info(
            "Ingest selected: %d chunks produced from %d chapters",
            len(chunks),
            len(chapter_indices),
        )

        if not chunks:
            raise ValueError("No chunks produced - check chapter indices")

        task.progress = "Storing chunks..."
        logger.info("Ingest selected: storing %d chunks to PostgreSQL", len(chunks))
        services.content_store.save_chunks(file_hash, chunks)

        task.progress = "Writing manifest..."
        logger.info("Ingest selected: writing manifest")
        num_stored_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection="",
            model="",
            output_dir=OUTPUT_DIR,
            num_chapters=num_stored_chapters,
            stored_chapter_indices=list(chapter_indices),
        )

        task.progress = "Persisting file..."
        logger.info("Ingest selected: persisting original file")
        file_ext = Path(filename).suffix.lstrip(".").lower()
        persist_file(file_hash, file_ext, file_content)

        if description or document_type or file_ext:
            services.content_store.save_metadata(
                file_hash,
                DocumentMetadata(
                    description=description, document_type=document_type, file_extension=file_ext
                ),
            )
            logger.info("Ingest selected: saved metadata for doc=%s", file_hash[:12])

        elapsed = time.perf_counter() - t0
        task.progress = "Complete"
        logger.info(
            "Ingest selected complete: %s, %d chunks from %d chapters in %.1fs",
            filename,
            len(chunks),
            num_stored_chapters,
            elapsed,
        )
        tmp_path.unlink()
        return f"Ingested {len(chunks)} chunks from {num_stored_chapters} chapters of {filename}"
    except Exception as e:
        task.progress = f"Error: {str(e)}"
        raise


@router.get("/documents/{file_hash}/structure", response_model=DocumentStructureOut)
async def get_document_structure(file_hash: str, services: ServicesDep) -> DocumentStructureOut:
    """Get detailed structure of a document with chapters."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

    chapters = _get_document_chapters(file_hash, services)
    logger.info("Document structure %s: %d chapters", file_hash[:12], len(chapters))

    return DocumentStructureOut(
        file_hash=file_hash,
        filename=doc_manifest.get("original_filename") or Path(doc_manifest["source_path"]).name,
        num_chapters=doc_manifest.get("num_chapters", 0),
        chapters=chapters,
    )


@router.get("/documents/{file_hash}/metadata", response_model=MetadataResponse)
async def get_metadata(file_hash: str, services: ServicesDep) -> MetadataResponse:
    """Get the user-provided metadata for a document."""
    meta = services.content_store.get_metadata(file_hash)
    if meta is None:
        return MetadataResponse(
            document_hash=file_hash, description="", document_type="", file_extension=""
        )
    return MetadataResponse(
        document_hash=file_hash,
        description=meta.description,
        document_type=meta.document_type,
        file_extension=meta.file_extension,
    )


@router.put("/documents/{file_hash}/metadata", response_model=MetadataResponse)
async def save_metadata(
    file_hash: str, req: MetadataRequest, services: ServicesDep
) -> MetadataResponse:
    """Save or update the user-provided metadata for a document."""
    metadata = DocumentMetadata(description=req.description, document_type=req.document_type)
    services.content_store.save_metadata(file_hash, metadata)
    return MetadataResponse(
        document_hash=file_hash,
        description=req.description,
        document_type=req.document_type,
    )


@router.get("/documents/{file_hash}/file")
async def get_document_file(file_hash: str, services: ServicesDep) -> FileResponse:
    """Get the original document file (PDF or EPUB) for viewing."""
    meta = services.content_store.get_metadata(file_hash)
    if meta is None or not meta.file_extension:
        raise HTTPException(status_code=404, detail="File not found or file type unknown")

    file_path = get_persisted_file(file_hash, meta.file_extension)
    if file_path is None:
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_types = {"pdf": "application/pdf", "epub": "application/epub+zip", "txt": "text/plain"}
    media_type = media_types.get(meta.file_extension, "application/octet-stream")
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=f"{file_hash}.{meta.file_extension}",
        content_disposition_type="inline",
    )


@router.get("/documents/{file_hash}/chapters/{chapter}/pdf")
async def get_chapter_pdf(file_hash: str, chapter: int, services: ServicesDep) -> StreamingResponse:
    """Get a chapter-specific PDF containing only the pages for that chapter.

    Chapter is 1-based (user-facing).
    """
    meta = services.content_store.get_metadata(file_hash)
    if meta is None or meta.file_extension != "pdf":
        raise HTTPException(status_code=404, detail="PDF not found")

    file_path = get_persisted_file(file_hash, meta.file_extension)
    if file_path is None:
        raise HTTPException(status_code=404, detail="File not found on disk")

    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)
    if doc_manifest is None or "chapters" not in doc_manifest:
        raise HTTPException(status_code=404, detail="Document structure not found")

    stored_chapters = [c for c in doc_manifest["chapters"] if c.get("stored", True)]
    if chapter < 1 or chapter > len(stored_chapters):
        raise HTTPException(status_code=404, detail="Chapter not found")

    manifest_chapter = stored_chapters[chapter - 1]
    sections = manifest_chapter.get("sections", [])

    if not sections:
        raise HTTPException(
            status_code=404,
            detail=(
                "Chapter page range not available. "
                "Document may have been ingested without chapter detection."
            ),
        )

    page_start = sections[0]["page_start"]
    page_end = sections[-1]["page_end"]

    doc = fitz.open(str(file_path))
    chapter_pdf = fitz.open()
    for page_num in range(page_start, page_end + 1):
        if page_num <= len(doc):
            chapter_pdf.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)

    output_buffer = chapter_pdf.tobytes()
    chapter_pdf.close()
    doc.close()

    filename = f"{manifest_chapter.get('title', f'Chapter {chapter}')}.pdf"

    async def iterfile():
        yield output_buffer

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(output_buffer)),
        },
    )


def _ingest_background(
    task: Task,
    file_content: bytes,
    filename: str,
    services: ServicesDep,
    document_type: str = "",
    description: str = "",
) -> str:
    """Background task to ingest an uploaded file."""
    t0 = time.perf_counter()
    try:
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)

        task.progress = f"Hashing {filename}"
        logger.info("Ingest: hashing %s", filename)
        file_hash = _hash_file(tmp_path)

        # Check if already ingested
        if services.content_store.has_file(file_hash):
            task.progress = "File already ingested"
            logger.info("Ingest: %s already ingested (hash %s)", filename, file_hash[:12])
            tmp_path.unlink()
            return f"File already ingested (hash {file_hash[:12]})"

        # Ingest the file (loads chapters and returns Document)
        task.progress = f"Loading {filename}"
        logger.info("Ingest: loading %s", filename)
        doc = ingest_file(
            tmp_path,
            loaders={
                ".pdf": load_pdf,
                ".epub": functools.partial(load_epub, epub_config=services.config.epub),
                ".txt": load_txt,
            },
            original_filename=filename,
        )
        if doc is None:
            raise ValueError("Failed to load document")

        # Chunk
        task.progress = "Chunking..."
        logger.info("Ingest: chunking document")
        splitter = ChapterAwareSplitter(
            max_tokens=services.config.chunking.max_tokens,
            overlap_tokens=services.config.chunking.overlap_tokens,
        )
        chunks = splitter.split(doc)
        logger.info("Ingest: %d chunks produced", len(chunks))

        # Store chunks in PostgreSQL
        task.progress = "Storing chunks..."
        logger.info("Ingest: storing %d chunks to PostgreSQL", len(chunks))
        services.content_store.save_chunks(file_hash, chunks)

        # Write manifest
        task.progress = "Writing manifest..."
        logger.info("Ingest: writing manifest")
        num_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection="",
            model="",
            output_dir=OUTPUT_DIR,
            num_chapters=num_chapters,
        )

        # Persist the original file
        task.progress = "Persisting file..."
        logger.info("Ingest: persisting original file")
        file_ext = Path(filename).suffix.lstrip(".").lower()
        persist_file(doc.file_hash, file_ext, file_content)

        # Persist metadata if provided at upload time
        if description or document_type or file_ext:
            file_hash = doc.file_hash
            services.content_store.save_metadata(
                file_hash,
                DocumentMetadata(
                    description=description, document_type=document_type, file_extension=file_ext
                ),
            )
            logger.info("Ingest: saved metadata for doc=%s", file_hash[:12])

        elapsed = time.perf_counter() - t0
        task.progress = "Complete"
        logger.info("Ingest complete: %s, %d chunks in %.1fs", filename, len(chunks), elapsed)
        tmp_path.unlink()
        return f"Ingested {len(chunks)} chunks from {filename}"
    except Exception as e:
        task.progress = f"Error: {str(e)}"
        raise


@router.post("/documents/ingest", response_model=IngestTaskOut)
async def ingest_document(
    services: ServicesDep,
    file: UploadFile = File(...),
    document_type: str = Form(""),
    description: str = Form(""),
) -> IngestTaskOut:
    """Upload and ingest a document."""
    # Read file content
    content = await file.read()

    # Submit background task
    task_id = services.task_registry.submit(
        _ingest_background,
        content,
        file.filename,
        services,
        document_type,
        description,
        task_type="ingest",
        filename=file.filename,
    )
    logger.info("Ingest submitted: %s -> task %s", file.filename, task_id)

    return IngestTaskOut(task_id=task_id, filename=file.filename)


@router.delete("/documents/{file_hash}")
async def delete_document(file_hash: str, services: ServicesDep) -> JSONResponse:
    """Delete a document from all stores."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info("Deleting document %s", file_hash[:12])
    errors = _delete_document(
        file_hash, doc_manifest, services.content_store, OUTPUT_DIR
    )

    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"Partial deletion failure for {file_hash[:12]}: {'; '.join(errors)}",
        )

    return JSONResponse(
        {"message": f"Deleted document {file_hash[:12]}"},
        status_code=200,
    )


@router.delete(
    "/documents/{file_hash}/chapters/{chapter_number}",
    response_model=ChapterDeleteResponse,
)
async def delete_chapter(
    file_hash: str, chapter_number: int, services: ServicesDep
) -> ChapterDeleteResponse:
    """Remove a single chapter from all stores.

    chapter_number is 1-based (user-facing). Internally converted to 0-based chapter_index.
    Stable-index strategy: other chapters keep their original indices; only the manifest
    entry for the removed chapter is deleted.
    """
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

    chapter_index = chapter_number - 1  # convert to 0-based

    # Validate chapter exists in manifest
    manifest_chapters = doc_manifest.get("chapters", [])
    chapter_entry = next((ch for ch in manifest_chapters if ch.get("index") == chapter_index), None)
    if chapter_entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter {chapter_number} not found in document",
        )

    # Reject removal if it would leave the document with zero chapters
    if len(manifest_chapters) <= 1:
        raise HTTPException(
            status_code=400,
            detail=("Cannot remove the only chapter. Delete the entire document instead."),
        )

    logger.info(
        "Deleting chapter %d (index=%d) from document %s",
        chapter_number,
        chapter_index,
        file_hash[:12],
    )
    errors: list[str] = []

    # 1. PostgreSQL — transactional; do first
    summaries_deleted = 0
    flashcards_deleted = 0
    try:
        # Count before deletion for response
        existing_summary = services.content_store.get_summary(file_hash, chapter_index)
        summaries_deleted = 1 if existing_summary is not None else 0
        existing_flashcards = services.content_store.get_flashcards(file_hash, chapter_index)
        flashcards_deleted = len(existing_flashcards)
        services.content_store.delete_chapter(file_hash, chapter_index)
    except Exception as e:
        logger.error("Failed to delete chapter %d from PostgreSQL: %s", chapter_index, e)
        errors.append(f"PostgreSQL: {e}")

    # 2. document_chunks
    chunks_deleted = 0
    try:
        services.content_store.delete_chunks_by_chapter(file_hash, chapter_index)
    except Exception as e:
        logger.error("Failed to delete chapter %d chunks from PostgreSQL: %s", chapter_index, e)
        errors.append(f"Chunks: {e}")

    # 3. Manifest
    try:
        remove_chapter_from_manifest(file_hash, chapter_index, OUTPUT_DIR)
    except Exception as e:
        logger.error("Failed to remove chapter %d from manifest: %s", chapter_index, e)
        errors.append(f"Manifest: {e}")

    if errors:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Partial deletion failure for chapter {chapter_number} "
                f"of {file_hash[:12]}: {'; '.join(errors)}"
            ),
        )

    return ChapterDeleteResponse(
        message=f"Removed chapter {chapter_number} from document {file_hash[:12]}",
        chunks_deleted=chunks_deleted,
        summaries_deleted=summaries_deleted,
        flashcards_deleted=flashcards_deleted,
    )


@router.post("/documents/create", response_model=CreateDocumentResponse)
async def create_document(
    req: CreateDocumentRequest, services: ServicesDep
) -> CreateDocumentResponse:
    """Create a custom document from pasted text."""
    file_hash = hashlib.sha256(req.content.encode("utf-8")).hexdigest()

    if services.content_store.has_file(file_hash):
        raise HTTPException(
            status_code=409,
            detail="Document with identical content already exists",
        )

    services.content_store.save_custom_document(file_hash, req.title, req.content)
    services.content_store.save_content(file_hash, req.content)
    services.content_store.save_metadata(
        file_hash,
        DocumentMetadata(
            description=req.description,
            document_type=req.document_type,
            file_extension="txt",
        ),
    )

    task_id = services.task_registry.submit(
        _ingest_custom_document,
        file_hash,
        req.title,
        req.content,
        services,
        task_type="ingest",
        filename=f"{req.title}.txt",
    )
    logger.info("Create document submitted: %s -> task %s", req.title, task_id)

    return CreateDocumentResponse(task_id=task_id, file_hash=file_hash, title=req.title)


def _ingest_custom_document(
    task: Task,
    file_hash: str,
    title: str,
    content: str,
    services: ServicesDep,
) -> str:
    """Background task to ingest a custom (pasted-text) document."""
    t0 = time.perf_counter()
    try:
        task.progress = "Building document structure..."
        logger.info("Custom ingest: building doc for %s", title)
        doc = build_document_from_text(title, content, file_hash, original_filename=f"{title}.txt")

        task.progress = "Chunking..."
        splitter = ChapterAwareSplitter(
            max_tokens=services.config.chunking.max_tokens,
            overlap_tokens=services.config.chunking.overlap_tokens,
        )
        chunks = splitter.split(doc)
        logger.info("Custom ingest: %d chunks", len(chunks))

        if not chunks:
            raise ValueError("No chunks produced from custom document")

        task.progress = "Storing chunks..."
        services.content_store.save_chunks(file_hash, chunks)

        task.progress = "Writing manifest..."
        num_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection="",
            model="",
            output_dir=OUTPUT_DIR,
            num_chapters=num_chapters,
        )

        elapsed = time.perf_counter() - t0
        task.progress = "Complete"
        logger.info("Custom ingest complete: %s, %d chunks in %.1fs", title, len(chunks), elapsed)
        return f"Ingested {len(chunks)} chunks from custom document '{title}'"
    except Exception as e:
        task.progress = f"Error: {str(e)}"
        raise


@router.post("/documents/{file_hash}/append", response_model=AppendContentResponse)
async def append_content(
    file_hash: str, req: AppendContentRequest, services: ServicesDep
) -> AppendContentResponse:
    """Append text to an existing custom document and re-process the new content."""
    existing = services.content_store.get_custom_document(file_hash)
    if existing is None:
        raise HTTPException(status_code=404, detail="Custom document not found")

    services.content_store.append_custom_document(file_hash, req.content)

    task_id = services.task_registry.submit(
        _append_custom_document,
        file_hash,
        req.content,
        services,
        task_type="ingest",
        filename=f"{file_hash[:12]}-append.txt",
    )
    logger.info("Append content submitted: doc %s -> task %s", file_hash[:12], task_id)

    return AppendContentResponse(task_id=task_id, file_hash=file_hash)


def _append_custom_document(
    task: Task,
    file_hash: str,
    new_content: str,
    services: ServicesDep,
) -> str:
    """Background task to ingest new content appended to a custom document."""
    t0 = time.perf_counter()
    try:
        task.progress = "Building new chapters..."
        temp_doc = build_document_from_text("append", new_content, file_hash)

        existing_chunks = services.content_store.get_chunks_by_file(file_hash)
        if existing_chunks:
            max_index = max(c.metadata.chapter_index for c in existing_chunks if c.metadata)
            base_index = max_index + 1
        else:
            base_index = 0

        for ch in temp_doc.chapters:
            ch.index += base_index

        task.progress = "Chunking new content..."
        splitter = ChapterAwareSplitter(
            max_tokens=services.config.chunking.max_tokens,
            overlap_tokens=services.config.chunking.overlap_tokens,
        )
        chunks = splitter.split(temp_doc)
        logger.info("Append ingest: %d new chunks (base_index=%d)", len(chunks), base_index)

        if not chunks:
            task.progress = "Complete (no new content to index)"
            return "No new chunks produced from appended content"

        task.progress = "Storing new chunks..."
        services.content_store.save_chunks(file_hash, chunks)

        task.progress = "Updating manifest..."
        documents = _list_documents()
        doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)
        if doc_manifest is not None:
            existing_chapters = doc_manifest.get("chapters", [])
            new_chapter_entries = []
            for ch in temp_doc.chapters:
                if ch.pages:
                    page_start = ch.pages[0].number
                    page_end = ch.pages[-1].number
                    sections_data = [
                        {"title": ch.title, "page_start": page_start, "page_end": page_end}
                    ]
                else:
                    sections_data = []
                new_chapter_entries.append(
                    {
                        "index": ch.index,
                        "title": ch.title,
                        "sections": sections_data,
                        "stored": True,
                    }
                )

            doc_manifest["chapters"] = existing_chapters + new_chapter_entries
            doc_manifest["num_chapters"] = len(doc_manifest["chapters"])
            doc_manifest["chunk_count"] = doc_manifest.get("chunk_count", 0) + len(chunks)

            safe_title = _safe_name(doc_manifest.get("title", file_hash))
            manifest_path = OUTPUT_DIR / safe_title / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, "w") as f:
                    json.dump(doc_manifest, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

        elapsed = time.perf_counter() - t0
        task.progress = "Complete"
        logger.info(
            "Append ingest complete: doc %s, %d new chunks in %.1fs",
            file_hash[:12],
            len(chunks),
            elapsed,
        )
        return f"Appended {len(chunks)} new chunks to document {file_hash[:12]}"
    except Exception as e:
        task.progress = f"Error: {str(e)}"
        raise


@router.get("/documents/{file_hash}/content", response_model=DocumentContentResponse)
async def get_document_content(file_hash: str, services: ServicesDep) -> DocumentContentResponse:
    """Get the raw text content for a document."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

    content = services.content_store.get_content(file_hash)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    num_chapters = doc_manifest.get("num_chapters", 0)
    return DocumentContentResponse(content=content, num_chapters=num_chapters)


@router.put("/documents/{file_hash}/content", response_model=UpdateContentResponse)
async def update_document_content(
    file_hash: str, req: UpdateContentRequest, services: ServicesDep
) -> UpdateContentResponse:
    """Update the raw text content for a document, triggering re-ingestion."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

    new_hash = hashlib.sha256(req.content.encode("utf-8")).hexdigest()

    if new_hash == file_hash:
        return UpdateContentResponse(same=True)

    old_summaries = services.content_store.get_summaries(file_hash)
    old_flashcards = services.content_store.get_flashcards(file_hash)

    preserved_summaries = len(old_summaries)
    preserved_flashcards = len(old_flashcards)

    if services.content_store.has_file(new_hash):
        raise HTTPException(
            status_code=409,
            detail="Document with identical content already exists",
        )

    errors = _delete_document(
        file_hash, doc_manifest, services.content_store, OUTPUT_DIR
    )
    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete old document: {'; '.join(errors)}",
        )

    task_id = services.task_registry.submit(
        _ingest_updated_document,
        new_hash,
        req.content,
        services,
        file_hash,
        len(old_summaries),
        len(old_flashcards),
        task_type="ingest",
        filename=f"{new_hash[:12]}.txt",
    )
    logger.info(
        "Update content submitted: old %s -> new %s -> task %s",
        file_hash[:12],
        new_hash[:12],
        task_id,
    )

    return UpdateContentResponse(
        same=False,
        new_hash=new_hash,
        task_id=task_id,
        preserved={"summaries": preserved_summaries, "flashcards": preserved_flashcards},
    )


def _ingest_updated_document(
    task: Task,
    file_hash: str,
    content: str,
    services: ServicesDep,
    old_hash: str,
    old_num_summaries: int,
    old_num_flashcards: int,
) -> str:
    """Background task to ingest an updated document while preserving old summaries/flashcards."""
    t0 = time.perf_counter()
    try:
        task.progress = "Building document structure..."
        logger.info("Update ingest: building doc for new hash %s", file_hash[:12])
        title = f"Document {file_hash[:12]}"
        doc = build_document_from_text(
            title, content, file_hash, original_filename=f"{file_hash[:12]}.txt"
        )

        task.progress = "Storing content..."
        services.content_store.save_content(file_hash, content)

        task.progress = "Chunking..."
        splitter = ChapterAwareSplitter(
            max_tokens=services.config.chunking.max_tokens,
            overlap_tokens=services.config.chunking.overlap_tokens,
        )
        chunks = splitter.split(doc)
        logger.info("Update ingest: %d chunks", len(chunks))

        if not chunks:
            raise ValueError("No chunks produced from updated document")

        task.progress = "Storing chunks..."
        services.content_store.save_chunks(file_hash, chunks)

        task.progress = "Writing manifest..."
        num_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection="",
            model="",
            output_dir=OUTPUT_DIR,
            num_chapters=num_chapters,
        )

        services.content_store.save_metadata(
            file_hash,
            DocumentMetadata(description="", document_type="", file_extension="txt"),
        )

        elapsed = time.perf_counter() - t0
        task.progress = "Complete"
        logger.info(
            "Update ingest complete: new %s, %d chunks in %.1fs",
            file_hash[:12],
            len(chunks),
            elapsed,
        )
        return f"Ingested {len(chunks)} chunks for updated document {file_hash[:12]}"
    except Exception as e:
        task.progress = f"Error: {str(e)}"
        raise
