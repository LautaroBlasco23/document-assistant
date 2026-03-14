import argparse
import logging
import sys
import time
from pathlib import Path

import requests
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from infrastructure.config import load_config

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

    ok = check_ollama(config.ollama.base_url)
    print(f"  Ollama ({config.ollama.base_url}): {'OK' if ok else 'FAIL'}")
    all_ok = all_ok and ok

    ok = check_qdrant(config.qdrant.url)
    print(f"  Qdrant ({config.qdrant.url}): {'OK' if ok else 'FAIL'}")
    all_ok = all_ok and ok

    ok = check_neo4j(config.neo4j.uri, config.neo4j.user, config.neo4j.password)
    print(f"  Neo4j  ({config.neo4j.uri}): {'OK' if ok else 'FAIL'}")
    all_ok = all_ok and ok

    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def run_ingest(path: str) -> int:
    from application.ingest import ingest_file
    from infrastructure.chunking.splitter import ChapterAwareSplitter
    from infrastructure.graph.entity_extractor import extract_entities
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.ollama import OllamaEmbedder, OllamaLLM
    from infrastructure.output.manifest import write_manifest
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    target = Path(path)

    files: list[Path] = []
    if target.is_dir():
        files = list(target.glob("*.pdf")) + list(target.glob("*.epub"))
    else:
        files = [target]

    if not files:
        print(f"No PDF/EPUB files found at {path}", file=sys.stderr)
        return 1

    embedder = OllamaEmbedder(config.ollama, EmbeddingCache())
    llm = OllamaLLM(config.ollama)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    neo4j.ensure_indexes()

    splitter = ChapterAwareSplitter(
        max_tokens=config.chunking.max_tokens,
        overlap_tokens=config.chunking.overlap_tokens,
    )

    output_dir = Path("data/output")
    processed = 0

    for file_path in files:
        print(f"Ingesting {file_path.name} ...")
        t0 = time.perf_counter()

        doc = ingest_file(file_path, config)
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
        neo4j.upsert_document(doc.file_hash, doc.title, doc.source_path)
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

def run_summarize(book_title: str, chapter_num: int) -> int:
    from application.agents.summarizer import SummarizerAgent
    from application.retriever import HybridRetriever
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.ollama import OllamaEmbedder, OllamaLLM
    from infrastructure.output.markdown_writer import write_summary
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    chapter_index = chapter_num - 1

    embedder = OllamaEmbedder(config.ollama, EmbeddingCache())
    llm = OllamaLLM(config.ollama)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, config)

    query = f"chapter {chapter_num} summary"
    filters = {"chapter": chapter_index}
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

    agent = SummarizerAgent(llm)
    summary = agent.summarize(chapter_obj, chunks)

    output_dir = Path("data/output")
    out_path = write_summary(doc, chapter_index, summary, chunks, output_dir)
    print(f"Summary written to {out_path}")
    neo4j.close()
    return 0


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

def run_ask(query: str, book: str | None, chapter: int | None) -> int:
    from application.agents.qa_agent import QAAgent
    from application.retriever import HybridRetriever
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.ollama import OllamaEmbedder, OllamaLLM
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()

    filters: dict = {}
    if chapter is not None:
        filters["chapter"] = chapter - 1

    embedder = OllamaEmbedder(config.ollama, EmbeddingCache())
    llm = OllamaLLM(config.ollama)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, config)

    chunks = retriever.retrieve(query, k=20, filters=filters or None)
    if not chunks:
        print("No relevant context found.", file=sys.stderr)
        neo4j.close()
        return 1

    agent = QAAgent(llm)
    answer = agent.answer(query, chunks)
    print(answer)
    neo4j.close()
    return 0


# ---------------------------------------------------------------------------
# Generate Markdown (all three outputs)
# ---------------------------------------------------------------------------

def run_generate_md(book_title: str, chapter_num: int) -> int:
    from application.agents.question_generator import QuestionGeneratorAgent
    from application.agents.summarizer import SummarizerAgent
    from application.retriever import HybridRetriever
    from core.model.document import Chapter, Document
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.llm.embedding_cache import EmbeddingCache
    from infrastructure.llm.ollama import OllamaEmbedder, OllamaLLM
    from infrastructure.output.markdown_writer import (
        write_flashcards,
        write_questions,
        write_summary,
    )
    from infrastructure.vectorstore.qdrant_store import QdrantStore

    config = load_config()
    chapter_index = chapter_num - 1

    embedder = OllamaEmbedder(config.ollama, EmbeddingCache())
    llm = OllamaLLM(config.ollama)
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, config)

    chunks = retriever.retrieve(
        f"chapter {chapter_num}", k=20, filters={"chapter": chapter_index}
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

    output_dir = Path("data/output")

    print("Generating summary ...")
    summary = SummarizerAgent(llm).summarize(chapter_obj, chunks)
    p1 = write_summary(doc, chapter_index, summary, chunks, output_dir)
    print(f"  -> {p1}")

    print("Generating questions ...")
    qas = QuestionGeneratorAgent(llm).generate(chunks)
    p2 = write_questions(doc, chapter_index, qas, output_dir)
    print(f"  -> {p2}")

    print("Generating flashcards ...")
    p3 = write_flashcards(doc, chapter_index, qas, output_dir)
    print(f"  -> {p3}")

    neo4j.close()
    return 0


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

    p_summarize = sub.add_parser("summarize", help="Generate chapter summary")
    p_summarize.add_argument("book", help="Book title (used as folder name)")
    p_summarize.add_argument("chapter", type=int, help="Chapter number (1-based)")

    p_ask = sub.add_parser("ask", help="Ask a question using RAG")
    p_ask.add_argument("query", help="Question to ask")
    p_ask.add_argument("--book", help="Restrict to a specific book")
    p_ask.add_argument("--chapter", type=int, help="Restrict to a specific chapter")

    p_gen = sub.add_parser("generate-md", help="Generate all markdown outputs for a chapter")
    p_gen.add_argument("book", help="Book title")
    p_gen.add_argument("chapter", type=int, help="Chapter number (1-based)")

    args = parser.parse_args()
    _setup_logging(args.log_format)

    if args.command == "check":
        print("Service health checks:")
        sys.exit(run_check())

    elif args.command == "ingest":
        sys.exit(run_ingest(args.path))

    elif args.command == "summarize":
        sys.exit(run_summarize(args.book, args.chapter))

    elif args.command == "ask":
        sys.exit(run_ask(args.query, args.book, args.chapter))

    elif args.command == "generate-md":
        sys.exit(run_generate_md(args.book, args.chapter))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
