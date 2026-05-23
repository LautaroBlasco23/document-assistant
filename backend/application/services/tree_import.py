"""Tree creation, document ingest, and YouTube import orchestration."""

import hashlib
import logging
import tempfile
import time
from pathlib import Path
from uuid import UUID, uuid4

from api.limit_checks import PlanLimitExceeded
from api.services import Services
from api.tasks import Task, set_task_progress
from core.model.knowledge_tree import KnowledgeChunk
from infrastructure.chunking.splitter import ChapterAwareSplitter
from infrastructure.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


def _parse_and_chunk(
    file_bytes: bytes,
    filename: str,
    tmp_path: Path,
    services: Services,
) -> tuple:
    """Shared: save temp file, call appropriate loader, chunk with ChapterAwareSplitter.

    Returns (doc, chunks, file_hash, images).
    images is a dict[str, bytes] for EPUBs, empty dict for other types.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    suffix = Path(filename).suffix.lower()
    images: dict[str, bytes] = {}

    if suffix == ".pdf":
        from infrastructure.ingest.pdf_loader import load_pdf as _load_pdf
        doc = _load_pdf(tmp_path, file_hash, filename)
    elif suffix == ".epub":
        from infrastructure.ingest.epub_loader import load_epub as _load_epub
        doc, images = _load_epub(tmp_path, file_hash, filename)
    elif suffix == ".txt":
        from infrastructure.ingest.txt_loader import load_txt as _load_txt
        doc = _load_txt(tmp_path, file_hash, filename)
        if doc is None:
            raise ValueError(f"No text could be extracted from '{filename}'.")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    splitter = ChapterAwareSplitter()
    chunks = splitter.split(doc)
    return doc, chunks, file_hash, images


def create_tree_from_file_task(
    task: Task,
    file_bytes: bytes,
    filename: str,
    tree_title: str,
    services: Services,
    chapter_indices: list[int] | None = None,
    user_id: UUID | None = None,
) -> dict:
    """Background task: parse file, create tree with chapters and knowledge documents."""
    t0 = time.perf_counter()
    try:
        set_task_progress(task, 5, "Saving uploaded file...")
        suffix = Path(filename).suffix.lower()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            set_task_progress(task, 10, "Parsing document...")
            doc, _, file_hash, images = _parse_and_chunk(file_bytes, filename, tmp_path, services)

            set_task_progress(task, 20, "Creating knowledge tree...")

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

            source_doc = services.kt_doc_store.create_document(
                tree_uid, None, doc.title or tree_title, "", is_main=False,
            )
            services.kt_doc_store.update_document_source_file(
                source_doc.id, str(tree_file_path), filename
            )

            chapter_count = len(chapters_to_process)
            if chapter_count == 0:
                set_task_progress(task, 100, "Done (no chapters found)")
                return {"tree_id": str(tree_uid), "chapter_count": 0}

            import fitz

            from core.model.document import Document as _Document

            splitter = ChapterAwareSplitter()
            all_kt_chunks = []

            for i, chapter in enumerate(chapters_to_process):
                chapter_number = i + 1
                pct_base = 25 + int(70 * i / chapter_count)
                chapter_title = chapter.title or f"Chapter {chapter_number}"
                set_task_progress(
                    task,
                    pct_base,
                    f"Processing chapter {chapter_number}/{chapter_count}: {chapter_title}...",
                )

                kt_chapter = services.kt_chapter_store.create_chapter(tree_uid, chapter_title)
                chapter_uid = kt_chapter.id

                single_chapter_doc = _Document(
                    source_path=doc.source_path,
                    title=doc.title,
                    file_hash=file_hash,
                    original_filename=filename,
                    chapters=[chapter],
                )

                chunks = splitter.split(single_chapter_doc)

                if chunks:
                    full_text = "\n\n".join(c.text for c in chunks)
                else:
                    full_text = "\n\n".join(p.text for p in chapter.pages)

                ch_page_start = chapter.pages[0].number if chapter.pages else None
                ch_page_end = chapter.pages[-1].number if chapter.pages else None

                ft = 'md' if suffix == '.epub' else None
                kt_doc = services.kt_doc_store.create_document(
                    tree_uid, chapter_uid, chapter_title, full_text, is_main=False,
                    page_start=ch_page_start,
                    page_end=ch_page_end,
                    file_type=ft,
                )
                doc_uid = kt_doc.id

                if suffix == ".epub" and images and chapter.images:
                    doc_images_dir = storage_dir / str(doc_uid) / "images"
                    doc_images_dir.mkdir(parents=True, exist_ok=True)
                    for img_ref in chapter.images:
                        if img_ref.name in images:
                            (doc_images_dir / img_ref.name).write_bytes(images[img_ref.name])
                    api_base = f"/api/knowledge-trees/{tree_uid}/documents/{doc_uid}/images"
                    updated_text = full_text
                    for img_ref in chapter.images:
                        placeholder = f"__IMG__{img_ref.name}__"
                        md_img = f"![{img_ref.alt}]({api_base}/{img_ref.name})"
                        updated_text = updated_text.replace(placeholder, md_img)
                    services.kt_doc_store.update_document(
                        doc_uid, chapter_title, updated_text
                    )
                    full_text = updated_text

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

            set_task_progress(task, 90, "Storing content chunks...")
            if all_kt_chunks:
                services.kt_content_store.save_chunks(all_kt_chunks)

            elapsed = time.perf_counter() - t0
            set_task_progress(task, 100, "Done")
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


def import_youtube_task(
    task: Task,
    url: str,
    tree_id: UUID,
    chapter_id: UUID | None,
    chapter_number: int | None,
    services: Services,
) -> dict:
    """Background task: fetch YouTube transcript and store as document."""
    from infrastructure.ingest.youtube_loader import (
        TranscriptUnavailable,
        VideoUnavailable,
        extract_video_id,
        fetch_metadata,
        fetch_transcript,
    )

    try:
        set_task_progress(task, 5, "Extracting video ID...")
        try:
            video_id = extract_video_id(url)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=str(exc))

        set_task_progress(task, 15, "Fetching video metadata...")
        try:
            meta = fetch_metadata(video_id)
        except VideoUnavailable as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(exc))

        set_task_progress(task, 35, "Fetching transcript...")
        try:
            transcript = fetch_transcript(video_id)
        except TranscriptUnavailable as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=str(exc))

        set_task_progress(task, 65, "Creating knowledge document...")
        kt_doc = services.kt_doc_store.create_youtube_document(
            tree_id=tree_id,
            chapter_id=chapter_id,
            title=meta.title,
            content=transcript,
            source_url=url,
        )

        if chapter_id is not None and chapter_number is not None:
            set_task_progress(task, 80, "Chunking transcript...")
            from core.model.document import Chapter, Document, Page

            lines = transcript.splitlines()
            pages = [Page(number=i + 1, text=line) for i, line in enumerate(lines) if line.strip()]
            chapter_obj = Chapter(index=0, title=meta.title, pages=pages)
            doc_obj = Document(
                source_path="",
                title=meta.title,
                file_hash="",
                original_filename="",
                chapters=[chapter_obj],
            )
            splitter = ChapterAwareSplitter()
            chunks = splitter.split(doc_obj)
            kt_chunks = [
                KnowledgeChunk(
                    id=UUID(c.id) if c.id else uuid4(),
                    tree_id=tree_id,
                    chapter_id=chapter_id,
                    doc_id=kt_doc.id,
                    chunk_index=j,
                    text=c.text,
                    token_count=c.token_count,
                )
                for j, c in enumerate(chunks)
            ]
            if kt_chunks:
                services.kt_content_store.save_chunks(kt_chunks)

        set_task_progress(task, 100, "Done")
        logger.info("Imported YouTube video %s as document %s", video_id, kt_doc.id)
        return {"doc_id": str(kt_doc.id), "title": meta.title}
    except Exception as exc:
        logger.error("YouTube import failed: %s", exc)
        raise


def ingest_file_task(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    file_bytes: bytes,
    filename: str,
    services: Services,
) -> dict:
    """Background task: parse file, chunk, store as knowledge document in existing chapter."""
    t0 = time.perf_counter()
    try:
        set_task_progress(task, 5, "Saving uploaded file...")
        suffix = Path(filename).suffix.lower()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            set_task_progress(task, 15, "Parsing document...")
            doc, chunks, file_hash, images = _parse_and_chunk(
                file_bytes, filename, tmp_path, services
            )

            set_task_progress(task, 40, "Chunking document...")

            full_text = "\n\n".join(c.text for c in chunks)

            if not full_text.strip():
                raise ValueError(
                    f"No text could be extracted from '{filename}'. "
                    "The file may be a scanned image, password-protected, or corrupt."
                )

            title = Path(filename).stem

            set_task_progress(task, 60, "Storing document...")
            ft = 'md' if suffix == '.epub' else None
            kt_doc = services.kt_doc_store.create_document(
                tree_id, chapter_id, title, full_text, is_main=False,
                file_type=ft,
            )
            doc_uid = kt_doc.id
            storage_dir = PROJECT_ROOT / "data" / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            file_path = storage_dir / f"{doc_uid}{suffix}"
            file_path.write_bytes(file_bytes)
            services.kt_doc_store.update_document_source_file(doc_uid, str(file_path), filename)

            if images and doc.chapters:
                doc_images_dir = storage_dir / str(doc_uid) / "images"
                doc_images_dir.mkdir(parents=True, exist_ok=True)
                for chapter in doc.chapters:
                    for img_ref in chapter.images:
                        if img_ref.name in images:
                            (doc_images_dir / img_ref.name).write_bytes(images[img_ref.name])
                api_base = f"/api/knowledge-trees/{tree_id}/documents/{doc_uid}/images"
                updated_text = full_text
                for chapter in doc.chapters:
                    for img_ref in chapter.images:
                        placeholder = f"__IMG__{img_ref.name}__"
                        md_img = f"![{img_ref.alt}]({api_base}/{img_ref.name})"
                        updated_text = updated_text.replace(placeholder, md_img)
                services.kt_doc_store.update_document(
                    doc_uid, title, updated_text
                )
                full_text = updated_text

            set_task_progress(task, 75, "Storing content chunks...")
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
            set_task_progress(task, 100, "Done")
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
