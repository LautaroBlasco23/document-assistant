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
infrastructure/ # Adapters: config loader, Ollama client, Qdrant, Neo4j
cli/            # CLI entry point
```

## Key decisions

- **No LlamaIndex/LangChain** — Direct `requests` to Ollama + `qdrant-client` + `neo4j` driver. Simpler, fewer deps, more debuggable.
- **No Whoosh** — Qdrant v1.7+ has built-in full-text search for BM25-style keyword search.
- **No spaCy (deferred)** — Start with LLM-based entity extraction via Ollama. Add spaCy only if extraction quality or speed demands it.
- **No Tesseract OCR (deferred)** — Most text PDFs/EPUBs won't need it. Add when encountering scanned docs.
- **uv** for dependency management (not pip+venv).
- **Idempotent ingestion** — Documents identified by file hash to avoid re-processing.

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

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## Development rules

- Domain models in `core/` must not import from `infrastructure/` or `application/`.
- Infrastructure adapters implement ports defined in `core/ports/`.
- Keep modules small and testable. No unnecessary abstractions.
- Pin Docker images to specific versions.
