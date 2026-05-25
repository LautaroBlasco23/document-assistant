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
from core.model.document import Chapter, Document, Page
from core.model.knowledge_tree import KnowledgeChapter, KnowledgeChunk
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


def split_chapter_into_ranges(
    tree_id: UUID,
    chapter_number: int,
    chapters: list,
    services: Services,
) -> list[KnowledgeChapter]:
    """Split a chapter into multiple chapter segments by page range.

    Each entry in ``chapters`` must have ``page_start``, ``page_end``, and
    optionally ``title`` attributes.  The entries must be contiguous and cover
    the full page range of the original document.

    Supports both PDF and EPUB source files.
    """
    import fitz

    from api.schemas.knowledge_tree import ChapterSplitEntry

    # 1. Get chapter and document
    all_chapters = services.kt_chapter_store.list_chapters(tree_id)
    chapter = next((c for c in all_chapters if c.number == chapter_number), None)
    if chapter is None:
        raise ValueError(f"Chapter {chapter_number} not found")

    docs = services.kt_doc_store.list_documents(tree_id, chapter.id)
    if not docs:
        raise ValueError(f"No document found for chapter {chapter_number}")
    doc = docs[0]

    # 2. Validate source
    if not doc.source_file_path:
        raise ValueError("Document has no source file")
    suffix = Path(doc.source_file_path).suffix.lower()
    if suffix not in (".pdf", ".epub"):
        raise ValueError("Split is only supported for PDF and EPUB documents")
    if doc.page_start is None or doc.page_end is None:
        raise ValueError("Document has no page range information")

    entries = [
        ChapterSplitEntry(**c) if not isinstance(c, ChapterSplitEntry) else c
        for c in chapters
    ]

    # 3. Semantic validation — entries use relative page offsets within [0, page_count]
    page_count = doc.page_end - doc.page_start
    if len(entries) < 2:
        raise ValueError("At least 2 chapter entries are required")
    for entry in entries:
        if entry.page_start < 0 or entry.page_end > page_count:
            raise ValueError(
                f"Entry range [{entry.page_start}, {entry.page_end}] is outside "
                f"valid relative range [0, {page_count}]"
            )
    for i in range(len(entries) - 1):
        if entries[i].page_end + 1 != entries[i + 1].page_start:
            raise ValueError(
                f"Non-contiguous ranges: [{entries[i].page_start}, {entries[i].page_end}] "
                f"and [{entries[i + 1].page_start}, {entries[i + 1].page_end}]"
            )
    if entries[0].page_start != 0:
        raise ValueError(
            f"First entry must start at relative page 0, got {entries[0].page_start}"
        )
    if entries[-1].page_end != page_count:
        raise ValueError(
            f"Last entry must end at relative page {page_count} "
            f"(document covers absolute pages {doc.page_start}–{doc.page_end}), "
            f"got {entries[-1].page_end}"
        )

    src_path = Path(doc.source_file_path)
    storage_dir = PROJECT_ROOT / "data" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    splitter = ChapterAwareSplitter()

    # 4. Extract sub-files — for PDF, open source once and extract all ranges in memory
    #    to avoid overwriting the source file mid-loop.
    #    doc.source_file_path is already a sub-PDF with pages numbered 0..N-1,
    #    so entry.page_start/entry.page_end are the correct 0-based page indices.
    if suffix == ".pdf":
        pdf_doc = fitz.open(str(src_path))
        _sub_pdfs = []
        for entry in entries:
            sub = fitz.open()
            sub.insert_pdf(
                pdf_doc,
                from_page=entry.page_start,
                to_page=entry.page_end,
            )
            _sub_pdfs.append(sub)
        pdf_doc.close()

    segment_paths: list[Path] = []
    segment_texts: list[str] = []
    segment_chunks_list: list[list] = []

    for idx, entry in enumerate(entries):
        if suffix == ".pdf":
            sub_path, sub_text, sub_chunks = _extract_pdf_range(
                _sub_pdfs[idx], doc, entry, storage_dir, splitter,
            )
        else:
            sub_path, sub_text, sub_chunks = _extract_epub_range(
                src_path, doc, entry, storage_dir, splitter,
            )
        segment_paths.append(sub_path)
        segment_texts.append(sub_text)
        segment_chunks_list.append(sub_chunks)

    if suffix == ".pdf":
        for sub in _sub_pdfs:
            sub.close()

    # 5. Shift subsequent chapters by (N - 1)
    delta = len(entries) - 1
    if delta > 0:
        services.kt_chapter_store.shift_chapter_numbers(
            tree_id, chapter_number + 1, delta
        )

    # 6. Update original document (first entry) — convert relative offsets to absolute
    abs_first_start = doc.page_start + entries[0].page_start
    abs_first_end = doc.page_start + entries[0].page_end
    first_text = segment_texts[0] if segment_texts[0].strip() else "(empty)"
    services.kt_doc_store.update_document(doc.id, chapter.title, first_text)
    services.kt_doc_store.update_document_page_range(
        doc.id,
        abs_first_start,
        abs_first_end,
    )
    if segment_paths[0] != src_path:
        services.kt_doc_store.update_document_source_file(
            doc.id, str(segment_paths[0]), doc.source_file_name
        )

    # 7. Create chapters + documents for entries 1..N-1
    result_chapters: list[KnowledgeChapter] = [chapter]
    for idx in range(1, len(entries)):
        seg_title = entries[idx].title or f"Chapter {chapter_number + idx}"
        new_chapter = services.kt_chapter_store.create_chapter_with_number(
            tree_id, chapter_number + idx, seg_title
        )

        seg_content = segment_texts[idx] if segment_texts[idx].strip() else "(empty)"
        abs_page_start = doc.page_start + entries[idx].page_start
        abs_page_end = doc.page_start + entries[idx].page_end
        new_doc = services.kt_doc_store.create_document(
            tree_id,
            new_chapter.id,
            seg_title,
            seg_content,
            is_main=False,
            page_start=abs_page_start,
            page_end=abs_page_end,
        )

        services.kt_doc_store.update_document_source_file(
            new_doc.id, str(segment_paths[idx]), doc.source_file_name
        )

        result_chapters.append(new_chapter)

    # 8. Delete old chunks for the original document
    services.kt_content_store.delete_chunks_by_doc_id(doc.id)

    # 9. Save new chunks for all segments
    all_new_chunks: list[KnowledgeChunk] = []
    for idx in range(len(entries)):
        ch = result_chapters[idx]
        seg_docs = services.kt_doc_store.list_documents(tree_id, ch.id)
        seg_doc_id = seg_docs[0].id if seg_docs else doc.id
        chunks = segment_chunks_list[idx]
        for j, c in enumerate(chunks):
            all_new_chunks.append(
                KnowledgeChunk(
                    id=UUID(c.id) if c.id else uuid4(),
                    tree_id=tree_id,
                    chapter_id=ch.id,
                    doc_id=seg_doc_id,
                    chunk_index=j,
                    text=c.text,
                    token_count=c.token_count,
                )
            )
    if all_new_chunks:
        services.kt_content_store.save_chunks(all_new_chunks)

    logger.info(
        "Split chapter %d into %d parts",
        chapter_number,
        len(entries),
    )
    return result_chapters


def _extract_pdf_range(
    sub_pdf,
    doc,
    entry,
    storage_dir: Path,
    splitter: ChapterAwareSplitter,
) -> tuple[Path, str, list]:
    """Save an in-memory PDF sub-document, extract text directly with absolute page numbers."""
    sub_path = storage_dir / f"{uuid4()}.pdf"
    sub_pdf.save(str(sub_path))

    file_hash = hashlib.sha256(sub_path.read_bytes()).hexdigest()

    pages = []
    for i in range(len(sub_pdf)):
        text = sub_pdf[i].get_text()
        abs_page = doc.page_start + entry.page_start + i
        pages.append(Page(number=abs_page, text=text))

    chapter = Chapter(index=0, title=doc.title or "Chapter", pages=pages)
    doc_obj = Document(
        source_path=str(sub_path),
        title=doc.title,
        file_hash=file_hash,
        original_filename=doc.source_file_name or "",
        chapters=[chapter],
    )
    chunks = splitter.split(doc_obj)
    text = "\n\n".join(p.text for p in pages)

    return sub_path, text, chunks


def _extract_epub_range(
    src_path: Path,
    doc,
    entry,
    storage_dir: Path,
    splitter: ChapterAwareSplitter,
) -> tuple[Path, str, list]:
    """Extract a spine-item range from an EPUB, extract text directly with absolute page numbers."""
    import ebooklib
    from ebooklib import epub
    from lxml import etree

    from infrastructure.ingest.epub_loader import _extract_markdown

    src_book = epub.read_epub(str(src_path))
    spine_items = list(src_book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    abs_start = doc.page_start + entry.page_start
    abs_end = doc.page_start + entry.page_end
    selected = spine_items[abs_start - 1 : abs_end]

    dst = epub.EpubBook()

    for key in ("title", "creator", "language", "publisher", "description"):
        vals = src_book.get_metadata("DC", key)
        if vals:
            val = vals[0][0] if isinstance(vals[0], tuple) else str(vals[0])
            dst.set_metadata("DC", key, val)

    identifiers = src_book.get_metadata("DC", "identifier")
    dst.set_identifier(str(identifiers[0][0]) if identifiers else str(uuid4()))

    toc = []
    spine = ["nav"]
    for i, sp_item in enumerate(selected):
        new_item = epub.EpubHtml(
            title=sp_item.file_name,
            file_name=sp_item.file_name,
            lang="en",
        )
        new_item.content = sp_item.get_content()
        dst.add_item(new_item)
        spine.append(new_item)
        toc.append(epub.Link(sp_item.file_name, sp_item.file_name, f"ch{i}"))

    for item in src_book.get_items():
        if item.get_type() not in (ebooklib.ITEM_DOCUMENT,):
            dst.add_item(item)

    dst.toc = toc
    dst.add_item(epub.EpubNcx())
    dst.add_item(epub.EpubNav())
    dst.spine = spine

    sub_path = storage_dir / f"{uuid4()}.epub"
    epub.write_epub(str(sub_path), dst, {})

    file_hash = hashlib.sha256(sub_path.read_bytes()).hexdigest()

    pages = []
    for i, sp_item in enumerate(selected):
        content = sp_item.get_content()
        root = etree.fromstring(content)
        text = _extract_markdown(root)
        abs_page = abs_start + i
        pages.append(Page(number=abs_page, text=text))

    chapter = Chapter(index=0, title=doc.title or "Chapter", pages=pages)
    doc_obj = Document(
        source_path=str(sub_path),
        title=doc.title,
        file_hash=file_hash,
        original_filename=doc.source_file_name or "",
        chapters=[chapter],
    )
    chunks = splitter.split(doc_obj)
    text = "\n\n".join(p.text for p in pages)

    return sub_path, text, chunks


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
