> NOTE: Legacy document flow removed. This file is out of date — re-run docs agent to refresh.

# Document Assistant

Local document reader and knowledge-tree learning platform with PostgreSQL persistence.

## Language

Python — justified exception to the Go preference. The NLP/ML ecosystem (PyMuPDF, ebooklib, Ollama client libraries) is Python-native with no viable Go alternatives.

## Architecture

Layered / DDD-inspired. Two parallel workflows coexist:

- **Legacy document flow**: Upload PDF/EPUB → ingest chunks → generate summaries + flashcards → test via flashcard exams
- **Knowledge tree flow**: Create/import knowledge tree → add chapters → attach documents (text or files) → generate questions → test via question exams

```
backend/        # All Python backend code (pyproject.toml + uv.lock live here)
  core/           # Domain models and port interfaces (no external deps)
    model/        # Document, Chapter, Page, Chunk, Summary, Flashcard, DocumentMetadata,
                  # ExamResult, KnowledgeTree, KnowledgeChapter, KnowledgeDocument,
                  # KnowledgeChunk, Question
    ports/        # ABCs: LLM, ContentStore, KnowledgeTreeStore, KnowledgeChapterStore,
                  # KnowledgeDocumentStore, KnowledgeContentStore
  application/    # Use cases (orchestration logic)
    agents/       # SummarizerAgent, FlashcardGeneratorAgent, QuestionGeneratorAgent
    ingest.py     # Ingestion use case (hash + load + idempotency check)
  infrastructure/ # Adapters: config loader, LLM clients, PostgreSQL
    ingest/       # pdf_loader, epub_loader, normalizer
    chunking/     # ChapterAwareSplitter
    llm/          # OllamaLLM, GroqLLM, OpenRouterLLM, HuggingFaceLLM, factory
    db/           # PostgresPool, ContentRepository, KnowledgeTreeRepository,
                  # schema.sql + migrations/
    output/       # markdown_writer, manifest
  api/            # FastAPI backend (wraps application layer, no duplication)
    routers/      # health, documents, chapters, content, exams, tasks, config, knowledge_trees
    schemas/      # Pydantic request/response models
    services.py   # Singleton service container (lifespan-managed)
    tasks.py      # In-memory task registry + ThreadPoolExecutor
  cli/            # CLI entry point (check, ingest, summarize, generate-md, config)
  tests/          # Unit and integration tests
config/         # YAML configuration (default.yml)
frontend/       # React + TypeScript + Tailwind SPA (Vite, port 5173)
  src/
    pages/      # Library, Document (summary/flashcard/exam tabs),
                # KnowledgeTree (documents/content/exam tabs), Settings
    components/ # Layout (Sidebar, Header, HealthBanner) + Shadcn-style UI primitives
    hooks/      # useHealth, useTask, useDocuments, useDocumentStructure
    stores/     # Zustand: AppStore, DocumentStore, TaskStore, FlashcardStore,
                # UploadStore, ExamStore, KnowledgeTreeStore
    services/   # API client abstraction (real/mock clients via VITE_MOCK env var)
    types/      # TypeScript domain and API types (domain.ts, api.ts, knowledge-tree.ts)
    lib/        # cn (classname helper)
    mocks/      # Mock data for development/testing
```

## Key decisions

- **No LlamaIndex/LangChain** — Direct `requests` to Groq/Ollama + `psycopg` for PostgreSQL. Simpler, fewer deps, more debuggable.
- **Groq as default LLM** — `GroqLLM` via `requests` to Groq's OpenAI-compatible API. Switch providers with `DOCASSIST_LLM_PROVIDER=ollama|openrouter|huggingface` or CLI `--provider`.
- **Groq rate limiter** — `GroqRateLimiter` (sliding window, 25/30 req/min threshold) is a module-level singleton in `groq_llm.py`. Proactively throttles before hitting the free-tier limit; also retries on 429 with exponential backoff.
- **Fast model for bulk tasks** — `create_fast_llm()` factory selects a smaller model for flashcard/summary/question generation. Knowledge tree question generation always uses `services.fast_llm`.
- **Word-based LLM batching** — Summarizer: 3500 words/call (map-reduce if larger). Flashcard generator: 3000 words/batch. Question generator: 2500 words/batch. Avoids fixed chunk counts, better aligns with LLM context windows.
- **JSON retry on malformed response** — `BaseAgent._call_json_with_retry` sends a correction prompt once if the LLM returns non-parseable JSON. Helps smaller/free models recover without failing silently.
- **Flashcard quality filter** — `_filter_low_quality` in `FlashcardGeneratorAgent` removes trivial cards post-generation: short fronts/backs, pattern-matched trivial questions, front/back overlap, and near-duplicates (Jaccard > 0.8). No extra LLM call needed.
- **Question validation per type** — `QuestionGeneratorAgent` validates each question against its schema (true_false, multiple_choice, matching, checkbox). Invalid questions are discarded silently; no re-prompting.
- **Four question types** — `true_false`, `multiple_choice`, `matching`, `checkbox`. Question data stored as JSONB in `knowledge_tree_questions`. Frontend mapper converts snake_case to camelCase.
- **Exam progression system** — Four levels: 0 (none), 1 (completed), 2 (gold), 3 (platinum). Only passed exams increment level (capped at 3). Failed exams trigger cooldown. Regenerating flashcards resets exam progress for that chapter.
- **PostgreSQL for all persistence** — 13 tables: legacy document tables + knowledge tree tables. Schema auto-applied on startup; idempotent SQL migrations in `infrastructure/db/migrations/`.
- **Task polling, not SSE** — Background tasks return `task_id`; frontend polls `GET /api/tasks/{task_id}` for progress. No streaming endpoints.
- **Chapter numbering** — API is **1-based** (user-facing). Legacy DB `chapter_index` is **0-based**. Knowledge trees have explicit 1-based `number` field. Routers convert 1-based input to 0-based before calling application layer.
- **Knowledge tree documents** — `KnowledgeDocument.chapter_id` can be null (tree-level) or bound to a chapter. Documents are chunked only when explicitly ingested via the import endpoint.
- **No Tesseract OCR (deferred)** — Most text PDFs/EPUBs won't need it. Add when encountering scanned docs.
- **uv** for dependency management (not pip+venv).
- **Idempotent ingestion** — Documents identified by SHA-256 file hash; `document_chunks` table checked before re-processing.
- **FastAPI wraps, not duplicates** — `api/` calls `application/` use cases directly; no logic is reimplemented.
- **In-memory task registry** — `ThreadPoolExecutor(max_workers=2)` for background tasks; no Celery/Redis needed for single-user local use.
- **Standalone SPA** — Vite dev server proxies `/api` to FastAPI in development; production build outputs static files to `frontend/dist/`.
- **Structured logging** — ANSI-colored terminal output with timestamps, log levels, and module names.
- **Source attribution** — Flashcards track `source_page`, `source_chunk_id`, and first ~400 chars of `source_text`, surfaced via the source context panel in the UI.

## Domain models

### Knowledge tree (primary flow)
- `KnowledgeTree`: `id` (UUID), `title`, `description`, `created_at`
- `KnowledgeChapter`: `id` (UUID), `tree_id`, `number` (1-based), `title`, `created_at` — UNIQUE(tree_id, number)
- `KnowledgeDocument`: `id` (UUID), `tree_id`, `chapter_id` (nullable), `title`, `content`, `is_main`, `created_at`, `updated_at`
- `KnowledgeChunk`: `id` (UUID), `tree_id`, `chapter_id`, `doc_id`, `chunk_index`, `text`, `token_count`
- `Question`: `id` (UUID), `tree_id`, `chapter_id`, `question_type` (true_false|multiple_choice|matching|checkbox), `question_data` (dict), `created_at`

### Legacy document flow
- `Document` → `Chapter` → `Page` → `Chunk` → `Summary` / `Flashcard`
- `ExamResult`: `id`, `document_hash`, `chapter_index`, `total_cards`, `correct_count`, `passed`, `completed_at`
- `DocumentMetadata`: `description`, `document_type`, `file_extension`

## Configuration

- YAML config at `config/default.yml` (project root, not inside `backend/`)
- Loaded via pydantic-settings with env var overrides (prefix: `DOCASSIST_`, nested delimiter: `__`)
- Example overrides:
  - `DOCASSIST_GROQ__API_KEY=gsk_...` — Groq API key (required when `llm_provider=groq`)
  - `DOCASSIST_LLM_PROVIDER=ollama` — switch to local Ollama
  - `DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434` — remote Ollama base URL
  - `DOCASSIST_POSTGRES__HOST=db-host` — remote PostgreSQL host

### LLM providers

| Provider | Main model | Fast model |
|----------|-----------|-----------|
| groq (default) | llama-3.3-70b-versatile | llama-3.1-8b-instant |
| ollama | qwen2.5:14b-instruct | qwen2.5:3b-instruct |
| openrouter | meta-llama/llama-3.3-70b-instruct:free | qwen/qwen2.5-7b-instruct:free |
| huggingface | Qwen/Qwen2.5-72B-Instruct | — |

### Exam cooldowns

| Event | Cooldown |
|-------|---------|
| After fail | 2 hours |
| Level 1 (completed) | 4 days |
| Level 2 (gold) | 14 days |
| Level 3 (platinum) | 30 days |

## External services

| Service | Default URL | Docker | Role |
|---------|-------------|--------|------|
| Groq API | `https://api.groq.com` | — | LLM inference (default; requires `DOCASSIST_GROQ__API_KEY`) |
| Ollama | localhost:11434 | Host-installed | Optional local LLM |
| PostgreSQL | localhost:5432 | `docker-compose.yml` | All persistence |

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

### Core

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Check LLM provider and PostgreSQL |
| GET | `/api/config` | Read current config |
| PATCH | `/api/config` | Update config (partial) |
| GET | `/api/tasks/{task_id}` | Poll task status + progress |
| GET | `/api/tasks/active` | List active background tasks |

### Legacy documents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/documents` | List all ingested documents |
| POST | `/api/documents/preview` | Preview chapter structure (no storage) |
| POST | `/api/documents/ingest` | Upload file → `{task_id}` |
| POST | `/api/documents/create` | Create custom document from text |
| GET | `/api/documents/{hash}/structure` | List chapters |
| DELETE | `/api/documents/{hash}` | Remove from all stores |
| GET | `/api/documents/{hash}/metadata` | Get document metadata |
| PATCH | `/api/documents/{hash}/metadata` | Update metadata |
| GET | `/api/documents/{hash}/content` | Get full stored text |
| POST | `/api/documents/{hash}/append` | Append text to custom document |
| PUT | `/api/documents/{hash}/content` | Replace full text content |
| POST | `/api/chapters/summarize` | Start background summary → `{task_id}` |
| POST | `/api/chapters/flashcards` | Start background flashcard generation → `{task_id}` |
| GET | `/api/documents/{hash}/summaries` | Get all stored summaries |
| GET | `/api/documents/{hash}/summaries/{chapter}` | Get summary for 1-based chapter |
| DELETE | `/api/documents/{hash}/summaries/{chapter}` | Delete summary |
| GET | `/api/documents/{hash}/flashcards` | Get flashcards (optional `?chapter=` `?status=`) |
| PATCH | `/api/documents/{hash}/flashcards/approve` | Approve flashcards by ID list |
| DELETE | `/api/documents/{hash}/flashcards/reject` | Delete (reject) flashcards by ID list |
| POST | `/api/documents/{hash}/flashcards/approve-all` | Approve all pending |

### Exams (legacy)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/exams` | Submit exam result (1-based chapter) |
| GET | `/api/documents/{hash}/exam-status` | Exam status + history for all chapters |
| GET | `/api/documents/{hash}/exam-status/{chapter}` | Status for 1-based chapter |

### Knowledge trees

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/knowledge-trees` | Create tree |
| GET | `/api/knowledge-trees` | List all trees |
| GET | `/api/knowledge-trees/{tree_id}` | Get tree by UUID |
| PUT | `/api/knowledge-trees/{tree_id}` | Update tree (title, description) |
| DELETE | `/api/knowledge-trees/{tree_id}` | Delete tree (cascades) |
| POST | `/api/knowledge-trees/preview` | Preview PDF/EPUB chapter structure |
| POST | `/api/knowledge-trees/import` | Import tree from file → `{task_id}` |
| POST | `/api/knowledge-trees/{tree_id}/chapters` | Create chapter |
| GET | `/api/knowledge-trees/{tree_id}/chapters` | List chapters |
| PUT | `/api/knowledge-trees/{tree_id}/chapters/{number}` | Update chapter title |
| DELETE | `/api/knowledge-trees/{tree_id}/chapters/{number}` | Delete chapter |
| POST | `/api/knowledge-trees/{tree_id}/documents` | Create document (tree-level or chapter) |
| GET | `/api/knowledge-trees/{tree_id}/documents` | List documents (optional `?chapter_id=`) |
| GET | `/api/knowledge-trees/{tree_id}/documents/{doc_id}` | Get document |
| PUT | `/api/knowledge-trees/{tree_id}/documents/{doc_id}` | Update document |
| DELETE | `/api/knowledge-trees/{tree_id}/documents/{doc_id}` | Delete document |
| POST | `/api/knowledge-trees/{tree_id}/chapters/{number}/documents/import` | Ingest file as chapter document → `{task_id}` |
| POST | `/api/knowledge-trees/{tree_id}/chapters/{number}/questions` | Start question generation → `{task_id}` |
| GET | `/api/knowledge-trees/{tree_id}/chapters/{number}/questions` | Get questions (optional `?type=`) |
| DELETE | `/api/knowledge-trees/{tree_id}/chapters/{number}/questions/{question_id}` | Delete question |
| GET | `/api/knowledge-trees/{tree_id}/chapters/{number}/content` | Get chapter chunks |

## Database schema (13 tables)

### Legacy document tables
- `document_chunks`: `file_hash`, `chapter_index` (0-based), `chunk_index`, `text`, `token_count`, `page_number`, `metadata` (JSON)
- `summaries`: `document_hash`, `chapter_index`, `content`, `description`, `bullets` (JSON text), `created_at`
- `flashcards`: `id` (UUID), `document_hash`, `chapter_index`, `front`, `back`, `source_page`, `source_chunk_id`, `source_text`, `status` (pending/approved), `created_at`
- `document_metadata`: `document_hash` (PK), `description`, `document_type`, `file_extension`
- `exam_results`: `id` (UUID), `document_hash`, `chapter_index`, `total_cards`, `correct_count`, `passed`, `completed_at`
- `document_content`: `file_hash` (PK), `content`, `created_at`
- `custom_documents`: `document_hash` (PK), `title`, `content`, `created_at`, `updated_at`

### Knowledge tree tables
- `knowledge_trees`: `id` (UUID PK), `title`, `description`, `created_at`
- `knowledge_chapters`: `id` (UUID PK), `tree_id` (FK cascade), `number` (1-based), `title` — UNIQUE(tree_id, number)
- `knowledge_documents`: `id` (UUID PK), `tree_id` (FK), `chapter_id` (nullable FK), `title`, `content`, `is_main`, `created_at`, `updated_at`
- `knowledge_content`: `id` (UUID PK), `tree_id`, `chapter_id`, `doc_id`, `chunk_index`, `text`, `token_count` — UNIQUE(doc_id, chunk_index)
- `knowledge_tree_questions`: `id` (UUID PK), `tree_id`, `chapter_id`, `question_type` (CHECK enum), `question_data` (JSONB), `created_at`
- `tasks`: `id`, `status`, `progress`, `progress_pct`, `result` (JSON), `error`, `task_type`, `doc_hash`, `chapter`, `book_title`, `filename`, `created_at`, `started_at`, `completed_at`

## Development rules

- Domain models in `core/` must not import from `infrastructure/` or `application/`.
- Infrastructure adapters implement ports defined in `core/ports/`.
- Keep modules small and testable. No unnecessary abstractions.
- Pin Docker images to specific versions.
- Integration tests are marked `@pytest.mark.integration` and skipped if services are unreachable.
- All modules use `logging.getLogger(__name__)`; root logger configured in `cli/main.py`.
- `api/` routers must use `ServicesDep` for dependency injection; never instantiate services directly inside routers.
- Chapter numbers: API accepts 1-based; routers convert to 0-based before calling application layer (same as CLI convention). Knowledge tree chapters use 1-based `number` throughout.
- Background tasks receive a `Task` object as first argument and write to `task.progress` for live status updates.
- Frontend dev server runs on port 5173; the FastAPI backend must be running independently on port 8000.
- Generated content (summaries, flashcards, questions) is persisted in PostgreSQL; content and knowledge_trees routers read from it.
- Question validation is per-type and strict — invalid questions are discarded silently (no re-prompting).
- Knowledge tree question generation always uses `services.fast_llm`.
- Regenerating flashcards for a chapter resets that chapter's exam progress (all exam results deleted).
