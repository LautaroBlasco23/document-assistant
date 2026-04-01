import argparse
import logging
import sys
import time
from pathlib import Path

import requests
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from infrastructure.config import PROJECT_ROOT, load_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service health check
# ---------------------------------------------------------------------------


def check_ollama(base_url: str) -> bool:
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def check_qdrant(url: str) -> bool:
    try:
        client = QdrantClient(url=url, timeout=5)
        client.get_collections()
        return True
    except Exception:
        return False


def check_neo4j(uri: str, user: str, password: str) -> bool:
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


def run_check() -> int:
    config = load_config()
    all_ok = True

    # ANSI color codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    checks = [
        ("Ollama", config.ollama.base_url, check_ollama(config.ollama.base_url)),
        ("Qdrant", config.qdrant.url, check_qdrant(config.qdrant.url)),
        (
            "Neo4j",
            config.neo4j.uri,
            check_neo4j(config.neo4j.uri, config.neo4j.user, config.neo4j.password),
        ),
    ]

    # Calculate column widths for alignment
    service_width = max(len(c[0]) for c in checks)
    url_width = max(len(c[1]) for c in checks)

    # Print header
    print(f"\n{BOLD}┌─ Service Health Status ─────────────────────────────────────┐{RESET}")
    print(f"{BOLD}│{RESET}")

    # Print each service
    for service, url, ok in checks:
        status_text = f"{GREEN}✓ OK{RESET}" if ok else f"{RED}✗ FAIL{RESET}"
        print(
            f"{BOLD}│{RESET}  {service.ljust(service_width)}  {url.ljust(url_width)}  {status_text}"
        )
        all_ok = all_ok and ok

    # Print footer
    print(f"{BOLD}│{RESET}")
    print(f"{BOLD}└────────────────────────────────────────────────────────────┘{RESET}\n")

    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def run_ingest(path: str, provider: str | None = None) -> int:
    import functools

    from application.ingest import ingest_file
    from infrastructure.chunking.splitter import ChapterAwareSplitter
    from infrastructure.graph.entity_extractor import extract_entities
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.ingest.epub_loader import load_epub
    from infrastructure.ingest.pdf_loader import load_pdf
    from infrastructure.ingest.txt_loader import load_txt
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.factory import create_embedder, create_llm
    from infrastructure.output.manifest import write_manifest
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    if provider is not None:
        config = config.model_copy(update={"llm_provider": provider})

    target = Path(path)

    files: list[Path] = []
    if target.is_dir():
        files = list(target.glob("*.pdf")) + list(target.glob("*.epub")) + list(target.glob("*.txt"))
    else:
        files = [target]

    if not files:
        print(f"No PDF/EPUB/TXT files found at {path}", file=sys.stderr)
        return 1

    embedder = create_embedder(config, EmbeddingCache())
    llm = create_llm(config)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    neo4j.ensure_indexes()

    splitter = ChapterAwareSplitter(
        max_tokens=config.chunking.max_tokens,
        overlap_tokens=config.chunking.overlap_tokens,
    )

    output_dir = PROJECT_ROOT / "data" / "output"
    processed = 0

    for file_path in files:
        print(f"Ingesting {file_path.name} ...")
        t0 = time.perf_counter()

        doc = ingest_file(
            file_path,
            loaders={
                ".pdf": load_pdf,
                ".epub": functools.partial(load_epub, epub_config=config.epub),
                ".txt": load_txt,
            },
            exists_fn=qdrant.has_file,
            original_filename=file_path.name,
        )
        if doc is None:
            print("  Skipped (already ingested or unsupported)")
            continue

        # Chunk
        print("  Chunking ...")
        chunks = splitter.split(doc)
        print(f"  {len(chunks)} chunks")

        # Embed
        print("  Embedding ...")
        texts = [c.text for c in chunks]
        vectors = embedder.embed(texts)

        # Ensure collection exists
        if vectors:
            qdrant.ensure_collection(vector_size=len(vectors[0]))

        # Upsert vectors
        print("  Upserting to Qdrant ...")
        qdrant.upsert(chunks, vectors)

        # Extract entities and store in graph
        print("  Extracting entities ...")
        neo4j.upsert_document(doc.file_hash, doc.title, doc.source_path, doc.original_filename)
        for chunk in chunks:
            entities = extract_entities(chunk.text, llm)
            neo4j.upsert_entities(entities, chunk)

        # Write manifest
        write_manifest(
            doc,
            chunk_count=len(chunks),
            collection=config.qdrant.collection_name,
            model=config.ollama.embedding_model,
            output_dir=output_dir,
        )

        elapsed = time.perf_counter() - t0
        print(f"  Done in {elapsed:.1f}s")
        processed += 1

    neo4j.close()
    print(f"\nIngested {processed}/{len(files)} file(s).")
    return 0 if processed > 0 else 1


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------


def run_summarize(book_title: str, chapter_num: int, provider: str | None = None) -> int:
    from application.agents.summarizer import SummarizerAgent
    from application.retriever import HybridRetriever
    from infrastructure.graph.entity_extractor import extract_entities
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.factory import create_embedder, create_fast_llm, create_llm
    from infrastructure.output.markdown_writer import write_summary
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    if provider is not None:
        config = config.model_copy(update={"llm_provider": provider})

    chapter_index = chapter_num - 1

    embedder = create_embedder(config, EmbeddingCache())
    llm = create_llm(config)
    fast_llm = create_fast_llm(config, llm)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, extract_entities)

    query = f"chapter {chapter_num} summary"
    filters = {"chapter": chapter_index, "file_hash": book_title}
    chunks = retriever.retrieve(query, k=20, filters=filters)

    if not chunks:
        print(f"No chunks found for book '{book_title}' chapter {chapter_num}.", file=sys.stderr)
        neo4j.close()
        return 1

    # Build a minimal Document for the writer
    from core.model.document import Chapter, Document

    chapter_obj = Chapter(index=chapter_index, title=f"Chapter {chapter_num}", pages=[])
    doc = Document(
        source_path=book_title,
        title=book_title,
        file_hash="",
        chapters=[chapter_obj],
    )

    agent = SummarizerAgent(fast_llm)
    summary = agent.summarize(chapter_obj, chunks)

    output_dir = PROJECT_ROOT / "data" / "output"
    out_path = write_summary(doc, chapter_index, summary, chunks, output_dir)
    print(f"Summary written to {out_path}")
    neo4j.close()
    return 0


# ---------------------------------------------------------------------------
# Generate Markdown (all three outputs)
# ---------------------------------------------------------------------------


def run_generate_md(book_title: str, chapter_num: int, provider: str | None = None) -> int:
    from application.agents.flashcard_generator import FlashcardGeneratorAgent
    from application.agents.summarizer import SummarizerAgent
    from application.retriever import HybridRetriever
    from core.model.document import Chapter, Document
    from infrastructure.graph.entity_extractor import extract_entities
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.factory import create_embedder, create_fast_llm, create_llm
    from infrastructure.output.markdown_writer import (
        write_flashcards,
        write_summary,
    )
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    if provider is not None:
        config = config.model_copy(update={"llm_provider": provider})

    chapter_index = chapter_num - 1

    embedder = create_embedder(config, EmbeddingCache())
    llm = create_llm(config)
    fast_llm = create_fast_llm(config, llm)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, extract_entities)

    chunks = retriever.retrieve(
        f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index, "file_hash": book_title}
    )

    if not chunks:
        print(f"No chunks found for chapter {chapter_num}.", file=sys.stderr)
        neo4j.close()
        return 1

    chapter_obj = Chapter(index=chapter_index, title=f"Chapter {chapter_num}", pages=[])
    doc = Document(
        source_path=book_title,
        title=book_title,
        file_hash="",
        chapters=[chapter_obj],
    )

    output_dir = PROJECT_ROOT / "data" / "output"

    print("Generating summary ...")
    summary = SummarizerAgent(fast_llm).summarize(chapter_obj, chunks)
    p1 = write_summary(doc, chapter_index, summary, chunks, output_dir)
    print(f"  -> {p1}")

    print("Generating flashcards ...")
    # Select LLM based on config
    if config.flashcard_model == "fast" and config.llm_provider == "openrouter":
        logger.warning(
            "flashcard_model=fast is not viable for openrouter (model too small); "
            "falling back to main model"
        )
        flashcard_llm = llm
    elif config.flashcard_model == "fast":
        flashcard_llm = fast_llm
    else:
        flashcard_llm = llm

    # Extract summary text for flashcard context
    summary_text = f"{summary['description']}\n" + "\n".join(f"- {b}" for b in summary.get("bullets", []))
    cards = FlashcardGeneratorAgent(flashcard_llm).generate(chunks, chapter_summary=summary_text)
    p2 = write_flashcards(doc, chapter_index, cards, output_dir)
    print(f"  -> {p2}")

    neo4j.close()
    return 0


# ---------------------------------------------------------------------------
# Prune orphaned documents
# ---------------------------------------------------------------------------


def run_prune() -> int:
    import json

    from application.delete_document import delete_document
    from infrastructure.db.content_repository import PostgresContentStore
    from infrastructure.db.postgres import PostgresPool
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    output_dir = PROJECT_ROOT / "data" / "output"

    if not output_dir.exists():
        print("No documents found (data/output/ does not exist).")
        return 0

    # Collect all manifests
    manifests = []
    for doc_dir in output_dir.iterdir():
        if not doc_dir.is_dir():
            continue
        manifest_file = doc_dir / "manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file) as f:
                    manifests.append(json.load(f))
            except Exception as e:
                print(f"  Warning: could not read {manifest_file}: {e}")

    if not manifests:
        print("No documents found in data/output/.")
        return 0

    qdrant = QdrantStore(config.qdrant)
    orphans = [m for m in manifests if not qdrant.has_file(m["file_hash"])]

    if not orphans:
        print(f"All {len(manifests)} document(s) have data in Qdrant. Nothing to prune.")
        return 0

    print(f"Found {len(orphans)} orphaned document(s) (no vectors in Qdrant):")
    for m in orphans:
        print(f"  - {m.get('original_filename') or m.get('title')} ({m['file_hash'][:12]})")

    neo4j = Neo4jStore(config.neo4j)
    pg_pool = PostgresPool(config.postgres)
    pg_pool.connect()
    content_store = PostgresContentStore(pg_pool)

    try:
        removed = 0
        for m in orphans:
            file_hash = m["file_hash"]
            errors = delete_document(file_hash, m, qdrant, neo4j, content_store, output_dir)
            if errors:
                print(f"  Partial failure for {file_hash[:12]}: {'; '.join(errors)}")
            else:
                print(f"  Deleted {m.get('original_filename') or m.get('title')}")
                removed += 1

        print(f"\nPruned {removed}/{len(orphans)} orphaned document(s).")
        return 0 if removed == len(orphans) else 1
    finally:
        neo4j.close()
        pg_pool.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _setup_logging(log_format: str) -> None:
    if log_format == "json":
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt="%H:%M:%S")


def main() -> None:
    parser = argparse.ArgumentParser(prog="document-assistant")
    parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="Log output format",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Check connectivity to all services")

    p_ingest = sub.add_parser("ingest", help="Ingest a PDF or EPUB file (or directory)")
    p_ingest.add_argument("path", help="Path to file or directory")
    p_ingest.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter", "huggingface"],
        help="LLM provider override (default: from config)",
    )

    p_summarize = sub.add_parser("summarize", help="Generate chapter summary")
    p_summarize.add_argument("book", help="Book title (used as folder name)")
    p_summarize.add_argument("chapter", type=int, help="Chapter number (1-based)")
    p_summarize.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter", "huggingface"],
        help="LLM provider override (default: from config)",
    )

    p_gen = sub.add_parser("generate-md", help="Generate all markdown outputs for a chapter")
    p_gen.add_argument("book", help="Book title")
    p_gen.add_argument("chapter", type=int, help="Chapter number (1-based)")
    p_gen.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter", "huggingface"],
        help="LLM provider override (default: from config)",
    )

    sub.add_parser("prune", help="Remove documents with no data in Qdrant (orphaned manifests)")

    args = parser.parse_args()
    _setup_logging(args.log_format)

    if args.command == "check":
        print("Service health checks:")
        sys.exit(run_check())

    elif args.command == "ingest":
        sys.exit(run_ingest(args.path, provider=getattr(args, "provider", None)))

    elif args.command == "summarize":
        sys.exit(run_summarize(args.book, args.chapter, provider=getattr(args, "provider", None)))

    elif args.command == "generate-md":
        sys.exit(run_generate_md(args.book, args.chapter, provider=getattr(args, "provider", None)))

    elif args.command == "prune":
        sys.exit(run_prune())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
