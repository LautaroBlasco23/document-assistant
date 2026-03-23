"""Document management endpoints."""

import json
import logging
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from api.deps import ServicesDep
from api.schemas.documents import (
    ChapterOut,
    DocumentOut,
    DocumentStructureOut,
    IngestTaskOut,
    MetadataRequest,
    MetadataResponse,
)
from api.tasks import Task
from application.ingest import _hash_file, ingest_file
from core.model.document_metadata import DocumentMetadata
from infrastructure.chunking.splitter import ChapterAwareSplitter
from infrastructure.graph.entity_extractor import extract_entities
from infrastructure.output.manifest import write_manifest
from infrastructure.output.markdown_writer import _safe_name

logger = logging.getLogger(__name__)

router = APIRouter()

OUTPUT_DIR = Path("data/output")


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

    chapters_from_manifest: dict[int, str] = {}
    if doc_manifest and "chapters" in doc_manifest:
        for ch in doc_manifest["chapters"]:
            chapters_from_manifest[ch.get("index", 0)] = ch.get("title", "")

    try:
        results = services.qdrant.search_by_file(file_hash)

        chapters_data: dict[int, int] = {}
        for chunk in results:
            chapter = chunk.metadata.chapter_index if chunk.metadata else 0
            chapters_data[chapter] = chapters_data.get(chapter, 0) + 1

        return [
            ChapterOut(
                number=ch + 1,
                title=chapters_from_manifest.get(ch, f"Chapter {ch + 1}"),
                num_chunks=count,
            )
            for ch, count in sorted(chapters_data.items())
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
        return MetadataResponse(document_hash=file_hash, description="", document_type="")
    return MetadataResponse(
        document_hash=file_hash,
        description=meta.description,
        document_type=meta.document_type,
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
        doc = ingest_file(tmp_path, services.config, original_filename=filename)
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

        # Persist metadata if provided at upload time
        if description or document_type:
            file_hash = doc.file_hash
            services.content_store.save_metadata(
                file_hash,
                DocumentMetadata(description=description, document_type=document_type),
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
        _ingest_background, content, file.filename, services, document_type, description
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
    errors: list[str] = []

    # Delete from Qdrant — attempt regardless of other failures
    try:
        services.qdrant.delete_by_source_file(file_hash)
    except Exception as e:
        logger.error(f"Failed to delete {file_hash} from Qdrant: {e}")
        errors.append(f"Qdrant: {e}")

    # Delete from Neo4j — attempt regardless of other failures
    try:
        services.neo4j.delete_document(file_hash)
    except Exception as e:
        logger.error(f"Failed to delete {file_hash} from Neo4j: {e}")
        errors.append(f"Neo4j: {e}")

    # Delete generated content from PostgreSQL
    try:
        services.content_store.delete_by_document(file_hash)
    except Exception as e:
        logger.error(f"Failed to delete content for {file_hash} from PostgreSQL: {e}")
        errors.append(f"PostgreSQL: {e}")

    # Delete manifest directory — use the same naming as write_manifest
    try:
        doc_dir = OUTPUT_DIR / _safe_name(doc_manifest["title"])
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
        else:
            logger.warning(f"Manifest directory not found for {file_hash}: {doc_dir}")
    except Exception as e:
        logger.error(f"Failed to delete manifest directory for {file_hash}: {e}")
        errors.append(f"Manifest: {e}")

    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"Partial deletion failure for {file_hash[:12]}: {'; '.join(errors)}",
        )

    return JSONResponse(
        {"message": f"Deleted document {file_hash[:12]}"},
        status_code=200,
    )
