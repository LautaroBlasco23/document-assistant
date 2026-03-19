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
api/            # FastAPI backend (wraps application layer, no duplication)
  routers/      # health, documents, search, ask, chapters, config, tasks
  schemas/      # Pydantic request/response models
  services.py   # Singleton service container (lifespan-managed)
  tasks.py      # In-memory task registry + ThreadPoolExecutor
  streaming.py  # SSE event helper
cli/            # CLI entry point (check, ingest, summarize, ask, generate-md)
electron/       # Electron desktop app
  src/main/     # Main process: spawn FastAPI, create BrowserWindow
  src/preload/  # contextBridge
  src/renderer/ # React + TypeScript + Tailwind UI (6 screens)
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
- **FastAPI wraps, not duplicates** — `api/` calls `application/` use cases directly; no logic is reimplemented.
- **In-memory task registry** — `ThreadPoolExecutor(max_workers=2)` for background ingestion/analysis tasks; no Celery/Redis needed for single-user local use.
- **SSE for streaming** — `StreamingResponse` in FastAPI + `fetch + ReadableStream` in renderer (not `EventSource`, which is GET-only).
- **Electron spawns uvicorn** — Main process starts `uv run uvicorn api.main:app --port 8000` and polls `/api/health` before showing the window.

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

# --- API backend ---

# Start FastAPI (standalone, no Electron)
uv run uvicorn api.main:app --port 8000

# Verify health
curl http://localhost:8000/api/health

# --- Electron desktop app ---

# Install Electron dependencies (first time only)
cd electron && npm install

# Run desktop app in dev mode (starts FastAPI + Vite + Electron)
npm run dev

# Build for production
npm run build
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Check Ollama, Qdrant, Neo4j |
| GET | `/api/documents` | List all ingested documents |
| POST | `/api/documents/ingest` | Upload file → `{task_id}` |
| GET | `/api/documents/{hash}/structure` | List chapters |
| DELETE | `/api/documents/{hash}` | Remove from all stores |
| POST | `/api/search` | Hybrid retrieval `{query, chapter?, k?}` |
| POST | `/api/ask` | SSE: stream Q&A answer |
| POST | `/api/chapters/summarize` | Background task → `{task_id}` |
| POST | `/api/chapters/questions` | Background task → `{task_id}` |
| POST | `/api/chapters/flashcards` | Background task → `{task_id}` |
| GET | `/api/config` | Read current config |
| GET | `/api/tasks/{task_id}` | Poll task status |

## Development rules

- Domain models in `core/` must not import from `infrastructure/` or `application/`.
- Infrastructure adapters implement ports defined in `core/ports/`.
- Keep modules small and testable. No unnecessary abstractions.
- Pin Docker images to specific versions.
- Integration tests are marked `@pytest.mark.integration` and skipped if services are unreachable.
- All modules use `logging.getLogger(__name__)`; root logger configured in `cli/main.py`.
- `api/` routers must use `ServicesDep` for dependency injection; never instantiate services directly inside routers.
- Chapter numbers: API accepts 1-based; routers convert to 0-based before calling application layer (same as CLI convention).
- Background tasks receive a `Task` object as first argument and write to `task.progress` for live status updates.
- Electron: the main process is responsible for the full subprocess lifecycle — spawn on app ready, kill on before-quit.
