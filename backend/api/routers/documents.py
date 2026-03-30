"""Document management endpoints."""

import functools
import json
import logging
import tempfile
import time
from pathlib import Path

import fitz
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from api.deps import ServicesDep
from api.schemas.documents import (
    ChapterDeleteResponse,
    ChapterOut,
    ChapterPreviewOut,
    DocumentOut,
    DocumentPreviewOut,
    DocumentStructureOut,
    IngestTaskOut,
    MetadataRequest,
    MetadataResponse,
)
from api.tasks import Task
from application.delete_document import delete_document as _delete_document
from application.ingest import _hash_file, ingest_file, preview_file
from core.model.document_metadata import DocumentMetadata
from infrastructure.chunking.splitter import ChapterAwareSplitter
from infrastructure.config import PROJECT_ROOT
from infrastructure.file_persistence import get_persisted_file, persist_file
from infrastructure.graph.entity_extractor import extract_entities
from infrastructure.ingest.epub_loader import load_epub, preview_epub
from infrastructure.ingest.pdf_loader import load_pdf, preview_pdf
from infrastructure.output.manifest import remove_chapter_from_manifest, write_manifest

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
    """Get chapter info for a document by querying Qdrant + manifest."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    chapters_from_manifest: dict[int, dict] = {}
    if doc_manifest and "chapters" in doc_manifest:
        for ch in doc_manifest["chapters"]:
            chapters_from_manifest[ch.get("index", 0)] = {
                "title": ch.get("title", ""),
                "sections": ch.get("sections", []),
            }

    try:
        results = services.qdrant.search_by_file(file_hash)

        chapters_data: dict[int, int] = {}
        for chunk in results:
            chapter = chunk.metadata.chapter_index if chunk.metadata else 0
            chapters_data[chapter] = chapters_data.get(chapter, 0) + 1

        sorted_chapters = sorted(chapters_data.items())
        return [
            ChapterOut(
                number=user_chapter_num,
                qdrant_index=actual_index,
                title=chapters_from_manifest.get(actual_index, {}).get(
                    "title", f"Chapter {user_chapter_num}"
                ),
                num_chunks=count,
                sections=chapters_from_manifest.get(actual_index, {}).get("sections", []),
            )
            for user_chapter_num, (actual_index, count) in enumerate(sorted_chapters, start=1)
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

        if services.qdrant.has_file(file_hash):
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

        task.progress = f"Embedding {len(chunks)} chunks..."
        logger.info("Ingest selected: embedding %d chunks", len(chunks))
        texts = [c.text for c in chunks]
        vectors = services.embedder.embed(texts)

        if vectors:
            services.qdrant.ensure_collection(vector_size=len(vectors[0]))

        task.progress = "Upserting to Qdrant..."
        logger.info("Ingest selected: upserting %d vectors to Qdrant", len(vectors))
        services.qdrant.upsert(chunks, vectors)

        task.progress = "Extracting entities..."
        logger.info("Ingest selected: extracting entities from %d chunks", len(chunks))
        services.neo4j.upsert_document(
            doc.file_hash, doc.title, doc.source_path, doc.original_filename
        )
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                task.progress = f"Extracting entities... {i}/{len(chunks)}"
            entities = extract_entities(chunk.text, services.fast_llm)
            services.neo4j.upsert_entities(entities, chunk)

        task.progress = "Writing manifest..."
        logger.info("Ingest selected: writing manifest")
        num_stored_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection=services.config.qdrant.collection_name,
            model=services.config.ollama.embedding_model,
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

    media_type = "application/pdf" if meta.file_extension == "pdf" else "application/epub+zip"
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
        if services.qdrant.has_file(file_hash):
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

        # Embed
        task.progress = f"Embedding {len(chunks)} chunks..."
        logger.info("Ingest: embedding %d chunks", len(chunks))
        texts = [c.text for c in chunks]
        vectors = services.embedder.embed(texts)

        # Ensure collection
        if vectors:
            services.qdrant.ensure_collection(vector_size=len(vectors[0]))

        # Upsert vectors
        task.progress = "Upserting to Qdrant..."
        logger.info("Ingest: upserting %d vectors to Qdrant", len(vectors))
        services.qdrant.upsert(chunks, vectors)

        # Extract entities and store in Neo4j
        task.progress = "Extracting entities..."
        logger.info("Ingest: extracting entities from %d chunks", len(chunks))
        services.neo4j.upsert_document(
            doc.file_hash, doc.title, doc.source_path, doc.original_filename
        )
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                task.progress = f"Extracting entities... {i}/{len(chunks)}"
            entities = extract_entities(chunk.text, services.fast_llm)
            services.neo4j.upsert_entities(entities, chunk)

        # Write manifest
        task.progress = "Writing manifest..."
        logger.info("Ingest: writing manifest")
        num_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection=services.config.qdrant.collection_name,
            model=services.config.ollama.embedding_model,
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
        file_hash, doc_manifest, services.qdrant, services.neo4j, services.content_store, OUTPUT_DIR
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

    # 2. Qdrant
    vectors_deleted = 0
    try:
        vectors_deleted = services.qdrant.delete_by_chapter(file_hash, chapter_index)
    except Exception as e:
        logger.error("Failed to delete chapter %d from Qdrant: %s", chapter_index, e)
        errors.append(f"Qdrant: {e}")

    # 3. Neo4j
    try:
        services.neo4j.delete_chapter(file_hash, chapter_index)
    except Exception as e:
        logger.error("Failed to delete chapter %d from Neo4j: %s", chapter_index, e)
        errors.append(f"Neo4j: {e}")

    # 4. Manifest
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
        vectors_deleted=vectors_deleted,
        summaries_deleted=summaries_deleted,
        flashcards_deleted=flashcards_deleted,
    )
