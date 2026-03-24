# Document Assistant

Local document reader agent with hybrid retrieval (vector + knowledge graph).

## Language

Python — justified exception to the Go preference. The NLP/ML ecosystem (PyMuPDF, ebooklib, embedding models, Ollama client libraries) is Python-native with no viable Go alternatives.

## Architecture

Layered / DDD-inspired:

```
backend/        # All Python backend code (pyproject.toml + uv.lock live here)
  core/           # Domain models and port interfaces (no external deps)
    model/        # Document, Chapter, Page, Chunk, Summary, Flashcard, DocumentMetadata
    ports/        # ABCs: Embedder, LLM, ContentStore
  application/    # Use cases (orchestration logic)
    agents/       # SummarizerAgent, FlashcardGeneratorAgent
    ingest.py     # Ingestion use case (hash + load + idempotency check)
    retriever.py  # HybridRetriever (vector + keyword + graph + rerank)
  infrastructure/ # Adapters: config loader, Ollama client, Qdrant, Neo4j, PostgreSQL
    ingest/       # pdf_loader, epub_loader, normalizer
    chunking/     # ChapterAwareSplitter
    llm/          # OllamaEmbedder, OllamaLLM, GroqLLM, EmbeddingCache, factory
    vectorstore/  # QdrantStore
    graph/        # Neo4jStore, entity_extractor
    db/           # PostgresPool, ContentRepository, schema + migrations
    output/       # markdown_writer, manifest
  api/            # FastAPI backend (wraps application layer, no duplication)
    routers/      # health, documents, chapters, content, config, tasks
    schemas/      # Pydantic request/response models
    services.py   # Singleton service container (lifespan-managed)
    tasks.py      # In-memory task registry + ThreadPoolExecutor
  cli/            # CLI entry point (check, ingest, summarize, generate-md, config)
  tests/          # Unit and integration tests
config/         # YAML configuration (default.yml)
frontend/       # React + TypeScript + Tailwind SPA (Vite, port 5173)
  src/
    pages/      # Library, Document (summary/flashcards tabs), Settings
    components/ # Layout (Sidebar, Header, HealthBanner) + Shadcn-style UI primitives
    hooks/      # useHealth, useTask, useDocuments, useDocumentStructure
    stores/     # Zustand: AppStore, DocumentStore, TaskStore, FlashcardStore, UploadStore
    services/   # API client abstraction (real/mock clients via VITE_MOCK env var)
    types/      # TypeScript domain and API types
    lib/        # cn (classname helper)
    mocks/      # Mock data for development/testing
```

## Key decisions

- **No LlamaIndex/LangChain** — Direct `requests` to Groq/Ollama + `qdrant-client` + `neo4j` driver. Simpler, fewer deps, more debuggable.
- **Groq as default LLM** — `GroqLLM` via `requests` to Groq's OpenAI-compatible API. Switch to Ollama with `DOCASSIST_LLM_PROVIDER=ollama` or CLI `--provider ollama`.
- **Groq rate limiter** — `GroqRateLimiter` (sliding window, 25/30 req/min threshold) is a module-level singleton in `groq_llm.py`. Proactively throttles before hitting the free-tier limit; also retries on 429 with exponential backoff.
- **Fast model for bulk tasks** — `create_fast_llm()` factory selects a smaller model (e.g. `llama-3.1-8b-instant` on Groq, `qwen2.5:3b-instruct` on Ollama) for flashcard/summary generation. Falls back to main model if not configured.
- **PostgreSQL for content persistence** — AI-generated summaries, flashcards, and user-provided document metadata stored in PostgreSQL (`summaries`, `flashcards`, `document_metadata` tables). Schema auto-applied on startup; idempotent SQL migrations in `infrastructure/db/migrations/`.
- **Task polling, not SSE** — Background tasks (summarize, flashcards) return a `task_id`; frontend polls `GET /api/tasks/{task_id}` for progress. No streaming endpoints.
- **No Whoosh** — Qdrant v1.7+ has built-in full-text search for BM25-style keyword search.
- **No spaCy (deferred)** — LLM-based entity extraction via Ollama with regex fallback. Add spaCy only if extraction quality or speed demands it.
- **No Tesseract OCR (deferred)** — Most text PDFs/EPUBs won't need it. Add when encountering scanned docs.
- **uv** for dependency management (not pip+venv).
- **Idempotent ingestion** — Documents identified by SHA-256 file hash; Qdrant checked before re-processing.
- **SQLite embedding cache** — `data/.cache/embeddings.db` keyed by SHA-256 of text; avoids re-embedding unchanged chunks.
- **Token counting** — Whitespace split (`len(text.split())`). No tiktoken dependency; upgrade if precision is needed.
- **FastAPI wraps, not duplicates** — `api/` calls `application/` use cases directly; no logic is reimplemented.
- **In-memory task registry** — `ThreadPoolExecutor(max_workers=2)` for background ingestion/analysis tasks; no Celery/Redis needed for single-user local use.
- **Standalone SPA** — Vite dev server proxies `/api` to FastAPI in development; production build outputs static files to `frontend/dist/`.
- **Structured logging** — ANSI-colored terminal output with timestamps, log levels, and module names.

## Configuration

- YAML config at `config/default.yml` (project root, not inside `backend/`)
- Loaded via pydantic-settings with env var overrides (prefix: `DOCASSIST_`, nested delimiter: `__`)
- Example overrides:
  - `DOCASSIST_GROQ__API_KEY=gsk_...` — Groq API key (required when `llm_provider=groq`)
  - `DOCASSIST_LLM_PROVIDER=ollama` — switch to local Ollama for LLM inference
  - `DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434` — remote Ollama for embeddings
  - `DOCASSIST_POSTGRES__HOST=db-host` — remote PostgreSQL host

## External services

| Service    | Default URL | Docker | Role |
|------------|-------------|--------|------|
| Groq API   | `https://api.groq.com` | — | LLM inference (default; requires `DOCASSIST_GROQ__API_KEY`) |
| Ollama     | localhost:11434 | Host-installed | Embeddings (`nomic-embed-text`); optional LLM fallback |
| Qdrant     | localhost:6333  | `docker-compose.yml` | Vector store |
| Neo4j      | localhost:7687  | `docker-compose.yml` | Knowledge graph |
| PostgreSQL | localhost:5432  | `docker-compose.yml` | Content persistence (summaries, flashcards, metadata) |

## Commands

```bash
# Start all infrastructure + backend + frontend (recommended)
make start

# Stop all services
make stop

# Start infrastructure only
docker compose up -d

# Install dependencies (from backend/)
cd backend && uv sync

# Health check all services
make check
# or
cd backend && uv run python -m cli.main check

# Ingest a file or directory
cd backend && uv run python -m cli.main ingest ../data/raw/book.pdf

# Generate all markdown outputs for chapter 1
cd backend && uv run python -m cli.main generate-md "book" 1

# Summarize a chapter
cd backend && uv run python -m cli.main summarize "book" 1

# Run tests (unit only)
cd backend && uv run pytest

# Run integration tests (requires running services)
cd backend && uv run pytest -m integration

# Lint
cd backend && uv run ruff check .

# --- API backend ---

# Start FastAPI (standalone)
cd backend && uv run uvicorn api.main:app --port 8000

# Verify health
curl http://localhost:8000/api/health

# --- Frontend web app ---

# Install frontend dependencies (first time only)
cd frontend && npm install

# Run frontend dev server (proxies /api to localhost:8000)
npm run dev

# Build for production (outputs to frontend/dist/)
npm run build
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Check Ollama, Qdrant, Neo4j, PostgreSQL |
| GET | `/api/documents` | List all ingested documents |
| POST | `/api/documents/ingest` | Upload file → `{task_id}` |
| GET | `/api/documents/{hash}/structure` | List chapters |
| DELETE | `/api/documents/{hash}` | Remove from all stores |
| POST | `/api/chapters/summarize` | Background task → `{task_id}` |
| POST | `/api/chapters/flashcards` | Background task → `{task_id}` |
| GET | `/api/documents/{hash}/summaries` | Get all stored summaries |
| GET | `/api/documents/{hash}/summaries/{chapter}` | Get summary for chapter (1-based) |
| GET | `/api/documents/{hash}/flashcards` | Get stored flashcards (optional `?chapter=` filter) |
| GET | `/api/config` | Read current config |
| PATCH | `/api/config` | Update config |
| GET | `/api/tasks/{task_id}` | Poll task status + progress |

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
- Frontend dev server runs on port 5173; the FastAPI backend must be running independently on port 8000.
- Generated content (summaries, flashcards) is persisted in PostgreSQL and served from the `content` router; agents write results, `content` router reads them.
