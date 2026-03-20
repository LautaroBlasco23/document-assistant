"""Document management endpoints."""

import json
import logging
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from api.deps import ServicesDep
from api.schemas.documents import DocumentOut, IngestTaskOut, DocumentStructureOut, ChapterOut
from api.tasks import Task
from application.ingest import ingest_file, _hash_file
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
    """Get chapter info for a document by querying Qdrant."""
    try:
        # Retrieve all chunks for this file_hash to determine chapter count
        # and chunks per chapter
        results = services.qdrant.search_by_file(file_hash)

        chapters_data: dict[int, int] = {}
        for chunk in results:
            chapter = chunk.metadata.chapter_index if chunk.metadata else 0
            chapters_data[chapter] = chapters_data.get(chapter, 0) + 1

        # Convert to list of ChapterOut
        return [
            ChapterOut(number=ch + 1, title=f"Chapter {ch + 1}", num_chunks=count)
            for ch, count in sorted(chapters_data.items())
        ]
    except Exception as e:
        logger.warning(f"Failed to get chapters for {file_hash}: {e}")
        return []


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(services: ServicesDep) -> list[DocumentOut]:
    """List all ingested documents."""
    documents = _list_documents()
    return [
        DocumentOut(
            file_hash=doc["file_hash"],
            filename=doc.get("original_filename") or Path(doc["source_path"]).name,
            num_chapters=doc.get("num_chapters", 0),
        )
        for doc in documents
    ]


@router.get("/documents/{file_hash}/structure", response_model=DocumentStructureOut)
async def get_document_structure(file_hash: str, services: ServicesDep) -> DocumentStructureOut:
    """Get detailed structure of a document with chapters."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

    chapters = _get_document_chapters(file_hash, services)

    return DocumentStructureOut(
        file_hash=file_hash,
        filename=doc_manifest.get("original_filename") or Path(doc_manifest["source_path"]).name,
        num_chapters=doc_manifest.get("num_chapters", 0),
        chapters=chapters,
    )


def _ingest_background(task: Task, file_content: bytes, filename: str, services: ServicesDep) -> str:
    """Background task to ingest an uploaded file."""
    try:
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)

        task.progress = f"Hashing {filename}"
        file_hash = _hash_file(tmp_path)

        # Check if already ingested
        if services.qdrant.has_file(file_hash):
            task.progress = "File already ingested"
            tmp_path.unlink()
            return f"File already ingested (hash {file_hash[:12]})"

        # Ingest the file (loads chapters and returns Document)
        task.progress = f"Loading {filename}"
        doc = ingest_file(tmp_path, services.config, original_filename=filename)
        if doc is None:
            raise ValueError("Failed to load document")

        # Chunk
        task.progress = "Chunking..."
        splitter = ChapterAwareSplitter(
            max_tokens=services.config.chunking.max_tokens,
            overlap_tokens=services.config.chunking.overlap_tokens,
        )
        chunks = splitter.split(doc)

        # Embed
        task.progress = f"Embedding {len(chunks)} chunks..."
        texts = [c.text for c in chunks]
        vectors = services.embedder.embed(texts)

        # Ensure collection
        if vectors:
            services.qdrant.ensure_collection(vector_size=len(vectors[0]))

        # Upsert vectors
        task.progress = "Upserting to Qdrant..."
        services.qdrant.upsert(chunks, vectors)

        # Extract entities and store in Neo4j
        task.progress = "Extracting entities..."
        services.neo4j.upsert_document(
            doc.file_hash, doc.title, doc.source_path, doc.original_filename
        )
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                task.progress = f"Extracting entities... {i}/{len(chunks)}"
            entities = extract_entities(chunk.text, services.llm)
            services.neo4j.upsert_entities(entities, chunk)

        # Write manifest
        task.progress = "Writing manifest..."
        num_chapters = len(set(c.metadata.chapter_index for c in chunks if c.metadata))
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection=services.config.qdrant.collection_name,
            model=services.config.ollama.embedding_model,
            output_dir=OUTPUT_DIR,
            num_chapters=num_chapters,
        )

        task.progress = "Complete"
        tmp_path.unlink()
        return f"Ingested {len(chunks)} chunks from {filename}"
    except Exception as e:
        task.progress = f"Error: {str(e)}"
        raise


@router.post("/documents/ingest", response_model=IngestTaskOut)
async def ingest_document(services: ServicesDep, file: UploadFile = File(...)) -> IngestTaskOut:
    """Upload and ingest a document."""
    # Read file content
    content = await file.read()

    # Submit background task
    task_id = services.task_registry.submit(
        _ingest_background, content, file.filename, services
    )

    return IngestTaskOut(task_id=task_id, filename=file.filename)


@router.delete("/documents/{file_hash}")
async def delete_document(file_hash: str, services: ServicesDep) -> JSONResponse:
    """Delete a document from all stores."""
    documents = _list_documents()
    doc_manifest = next((d for d in documents if d["file_hash"] == file_hash), None)

    if not doc_manifest:
        raise HTTPException(status_code=404, detail="Document not found")

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
