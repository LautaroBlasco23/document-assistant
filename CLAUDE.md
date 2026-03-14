# Document Assistant

Local document reader agent with hybrid retrieval (vector + knowledge graph).

## Language

Python — justified exception to the Go preference. The NLP/ML ecosystem (PyMuPDF, ebooklib, embedding models, Ollama client libraries) is Python-native with no viable Go alternatives.

## Architecture

Layered / DDD-inspired:

```
core/           # Domain models and port interfaces (no external deps)
  model/        # Document, Chapter, Page, Chunk dataclasses
  ports/        # ABCs: Embedder, LLM
application/    # Use cases (orchestration logic)
  agents/       # Summarizer, QA, QuestionGenerator agents
  ingest.py     # Ingestion use case (hash + load + idempotency check)
  retriever.py  # HybridRetriever (vector + keyword + graph + rerank)
infrastructure/ # Adapters: config loader, Ollama client, Qdrant, Neo4j
  ingest/       # pdf_loader, epub_loader, normalizer
  chunking/     # ChapterAwareSplitter
  llm/          # OllamaClient, OllamaEmbedder, OllamaLLM, EmbeddingCache
  vectorstore/  # QdrantStore
  graph/        # Neo4jStore, entity_extractor
  output/       # markdown_writer, manifest
cli/            # CLI entry point (check, ingest, summarize, ask, generate-md)
```

## Key decisions

- **No LlamaIndex/LangChain** — Direct `requests` to Ollama + `qdrant-client` + `neo4j` driver. Simpler, fewer deps, more debuggable.
- **No Whoosh** — Qdrant v1.7+ has built-in full-text search for BM25-style keyword search.
- **No spaCy (deferred)** — LLM-based entity extraction via Ollama with regex fallback. Add spaCy only if extraction quality or speed demands it.
- **No Tesseract OCR (deferred)** — Most text PDFs/EPUBs won't need it. Add when encountering scanned docs.
- **uv** for dependency management (not pip+venv).
- **Idempotent ingestion** — Documents identified by SHA-256 file hash; Qdrant checked before re-processing.
- **SQLite embedding cache** — `data/.cache/embeddings.db` keyed by SHA-256 of text; avoids re-embedding unchanged chunks.
- **Token counting** — Whitespace split (`len(text.split())`). No tiktoken dependency; upgrade if precision is needed.

## Configuration

- YAML config at `config/default.yml`
- Loaded via pydantic-settings with env var overrides (prefix: `DOCASSIST_`, nested delimiter: `__`)
- Example override: `DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434`

## External services

| Service | Default URL | Docker |
|---------|-------------|--------|
| Ollama  | localhost:11434 | Host-installed |
| Qdrant  | localhost:6333  | `docker/docker-compose.yml` |
| Neo4j   | localhost:7687  | `docker/docker-compose.yml` |

## Commands

```bash
# Start infrastructure
docker compose -f docker/docker-compose.yml up -d

# Install dependencies
uv sync

# Health check all services
uv run python -m cli.main check

# Ingest a file or directory
uv run python -m cli.main ingest data/raw/book.pdf

# Generate all markdown outputs for chapter 1
uv run python -m cli.main generate-md "book" 1

# Ask a question
uv run python -m cli.main ask "What is the main argument?" --book "book"

# Run tests (unit only)
uv run pytest

# Run integration tests (requires running services)
uv run pytest -m integration

# Lint
uv run ruff check .
```

## Development rules

- Domain models in `core/` must not import from `infrastructure/` or `application/`.
- Infrastructure adapters implement ports defined in `core/ports/`.
- Keep modules small and testable. No unnecessary abstractions.
- Pin Docker images to specific versions.
- Integration tests are marked `@pytest.mark.integration` and skipped if services are unreachable.
- All modules use `logging.getLogger(__name__)`; root logger configured in `cli/main.py`.
