# Document Assistant

Local document reader and knowledge-tree learning platform with PostgreSQL persistence and user authentication.

## Language

Python — justified exception to the Go preference. The NLP/ML ecosystem (PyMuPDF, ebooklib, Ollama client libraries) is Python-native with no viable Go alternatives.

## Architecture

Layered / DDD-inspired. Multi-user knowledge tree platform with JWT authentication and plan-based resource limits.

```
backend/        # All Python backend code (pyproject.toml + uv.lock live here)
  core/           # Domain models and port interfaces (no external deps)
    model/        # User, SubscriptionPlan, UserSubscription, UserLimits, KnowledgeTree,
                  # KnowledgeChapter, KnowledgeDocument, KnowledgeChunk, Flashcard, Question
    ports/        # ABCs: LLM, ContentStore, KnowledgeTreeStore, KnowledgeChapterStore,
                  # KnowledgeDocumentStore, KnowledgeContentStore, UserStore, SubscriptionStore
  application/    # Use cases (orchestration logic)
    agents/       # FlashcardGeneratorAgent, QuestionGeneratorAgent, DocumentChatAgent
  infrastructure/ # Adapters: config loader, LLM clients, PostgreSQL, JWT
    auth/         # JWT token handling, password hashing (bcrypt)
    ingest/       # pdf_loader, epub_loader, normalizer
    chunking/     # ChapterAwareSplitter
    llm/          # OllamaLLM, GroqLLM, OpenRouterLLM, HuggingFaceLLM, factory
    db/           # PostgresPool, UserRepository, SubscriptionRepository, KnowledgeTreeRepository,
                  # schema.sql + migrations/
  api/            # FastAPI backend (wraps application layer, no duplication)
    routers/      # health, config, tasks, auth, users, knowledge_trees, chat
    schemas/      # Pydantic request/response models
    services.py   # Singleton service container (lifespan-managed)
    tasks.py      # In-memory task registry + ThreadPoolExecutor
    auth.py       # JWT validation + CurrentUser dependency
    limit_checks.py # Plan-based resource limit enforcement
  cli/            # CLI entry point (check, ingest, summarize, generate-md, config)
  tests/          # Unit and integration tests
config/         # YAML configuration (default.yml)
frontend/       # React + TypeScript + Tailwind SPA (Vite, port 5173)
  src/
    auth/       # AuthContext (login/register/logout), ProtectedRoute
    pages/      # Library, KnowledgeTree (with unified document reader tab), Settings, Auth pages
    components/ # Layout (Sidebar, Header, HealthBanner), DocumentReader, ChatPanel, PdfPagesView
    hooks/      # useHealth, useTask, useDocuments, etc.
    stores/     # Zustand: AppStore, AuthStore, KnowledgeTreeStore, etc.
    services/   # API client abstraction
    types/      # TypeScript domain and API types
    lib/        # cn (classname helper), pdf-text extraction
    mocks/      # Mock data for development/testing
```

## Key decisions

- **User authentication & multi-tenancy** — JWT tokens (7-day expiry). All knowledge trees owned by user. Login/register/logout via FastAPI `/auth/` endpoints. Frontend stores token in localStorage, requests include Bearer token in Authorization header.
- **Plan-based resource limits** — Free plan: 200 documents, 3 knowledge trees. Subscription plans in DB (slug, name, max_documents, max_knowledge_trees). Router limit checks before write operations. `PlanLimitExceeded` exception raised on violation.
- **Per-request generation parameters** — `GenerationParams` dataclass (temperature, top_p, max_tokens) passed to all LLM calls. Frontend generation settings page controls these per-request. All LLM adapters accept params.
- **No LlamaIndex/LangChain** — Direct `requests` to Groq/Ollama + `psycopg` for PostgreSQL. Simpler, fewer deps, more debuggable.
- **Groq as default LLM** — `GroqLLM` via `requests` to Groq's OpenAI-compatible API. Switch providers with `DOCASSIST_LLM_PROVIDER=ollama|openrouter|huggingface` or CLI `--provider`.
- **Groq rate limiter** — `GroqRateLimiter` (sliding window, 25/30 req/min threshold) is a module-level singleton in `groq_llm.py`. Proactively throttles before hitting the free-tier limit; also retries on 429 with exponential backoff.
- **Fast model for bulk tasks** — `create_fast_llm()` factory selects a smaller model for flashcard/summary/question generation. Knowledge tree question generation always uses `services.fast_llm`.
- **Word-based LLM batching** — Summarizer: 3500 words/call (map-reduce if larger). Flashcard generator: 3000 words/batch. Question generator: 2500 words/batch. Avoids fixed chunk counts, better aligns with LLM context windows.
- **JSON retry on malformed response** — `BaseAgent._call_json_with_retry` sends a correction prompt once if the LLM returns non-parseable JSON. Helps smaller/free models recover without failing silently.
- **Flashcard quality filter** — `_filter_low_quality` in `FlashcardGeneratorAgent` removes trivial cards post-generation: short fronts/backs, pattern-matched trivial questions, front/back overlap, and near-duplicates (Jaccard > 0.8). No extra LLM call needed.
- **Question validation per type** — `QuestionGeneratorAgent` validates each question against its schema (true_false, multiple_choice, matching, checkbox). Invalid questions are discarded silently; no re-prompting.
- **Four question types** — `true_false`, `multiple_choice`, `matching`, `checkbox`. Question data stored as JSONB in `knowledge_tree_questions`. Frontend mapper converts snake_case to camelCase.
- **Document chat agent** — `DocumentChatAgent` grounds LLM responses in extracted PDF/EPUB text. User text selection triggers context menu → "Ask definition in chat" → DocumentReader chat panel.
- **Unified document reader** — Single component (PDF + EPUB) with integrated chat panel, virtualized PDF rendering, resizable sidebars, page navigation per chapter. Stores panel widths in localStorage.
- **Markdown rendering in chat** — ChatPanel uses react-markdown to render assistant replies with code blocks, lists, emphasis.
- **PostgreSQL for all persistence** — 16 tables: user auth, subscriptions, knowledge tree data, tasks. Schema auto-applied on startup; idempotent SQL migrations in `infrastructure/db/migrations/`.
- **Task polling, not SSE** — Background tasks return `task_id`; frontend polls `GET /api/tasks/{task_id}` for progress. No streaming endpoints.
- **Chapter numbering** — Knowledge tree chapters: 1-based `number` field throughout (API and DB). User-facing always 1-based.
- **Knowledge tree documents** — `KnowledgeDocument.chapter_id` can be null (tree-level) or bound to a chapter. Documents are chunked only when explicitly ingested via the import endpoint. Stores source_file_path, source_file_name, page_start, page_end (for PDF/EPUB chapter slicing).
- **No Tesseract OCR (deferred)** — Most text PDFs/EPUBs won't need it. Add when encountering scanned docs.
- **uv** for dependency management (not pip+venv).
- **Idempotent ingestion** — Documents identified by SHA-256 file hash; `knowledge_content` table checked before re-processing.
- **FastAPI wraps, not duplicates** — `api/` calls `application/` use cases directly; no logic is reimplemented.
- **In-memory task registry** — `ThreadPoolExecutor(max_workers=2)` for background tasks; no Celery/Redis needed for single-user local use.
- **Standalone SPA** — Vite dev server proxies `/api` to FastAPI in development; production build outputs static files to `frontend/dist/`.
- **Structured logging** — ANSI-colored terminal output with timestamps, log levels, and module names.
- **Source attribution** — Flashcards track source context and reference to original document/chunk.

## Domain models

### User & Subscription
- `User`: `id` (UUID), `email` (UNIQUE), `password_hash`, `display_name`, `is_active`, `created_at`, `updated_at`
- `SubscriptionPlan`: `id` (UUID), `slug` (UNIQUE), `name`, `description`, `max_documents`, `max_knowledge_trees`, `is_active`, `created_at`
- `UserSubscription`: `id` (UUID), `user_id` (FK), `plan_id` (FK), `assigned_at` — UNIQUE(user_id)
- `UserLimits`: `max_documents`, `max_knowledge_trees`, `current_documents`, `current_knowledge_trees`, `can_create_document`, `can_create_tree`

### Knowledge tree (primary flow)
- `KnowledgeTree`: `id` (UUID), `user_id` (FK), `title`, `description`, `created_at`
- `KnowledgeChapter`: `id` (UUID), `tree_id` (FK), `number` (1-based), `title`, `created_at` — UNIQUE(tree_id, number)
- `KnowledgeDocument`: `id` (UUID), `tree_id` (FK), `chapter_id` (nullable FK), `title`, `content`, `is_main`, `source_file_path`, `source_file_name`, `page_start`, `page_end`, `created_at`, `updated_at`
- `KnowledgeChunk`: `id` (UUID), `tree_id` (FK), `chapter_id` (FK), `doc_id` (FK), `chunk_index`, `text`, `token_count`, `created_at`
- `Flashcard`: `id` (UUID), `tree_id` (FK), `chapter_id` (FK), `doc_id` (nullable FK), `front`, `back`, `source_text`, `created_at`
- `Question`: `id` (UUID), `tree_id` (FK), `chapter_id` (FK), `question_type` (true_false|multiple_choice|matching|checkbox), `question_data` (JSONB), `created_at`

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

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user with free plan → `{access_token, expires_in_days}` |
| POST | `/api/auth/login` | Authenticate → `{access_token, expires_in_days}` |
| GET | `/api/auth/me` | Get current user profile (requires Bearer token) |

### Core

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Check LLM provider and PostgreSQL |
| GET | `/api/config` | Read current config |
| PATCH | `/api/config` | Update config (partial) |
| GET | `/api/tasks/{task_id}` | Poll task status + progress |

### Users

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users/me/limits` | Get current usage and plan limits |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Chat with AI about document context (requires Bearer token) |

### Knowledge trees

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/knowledge-trees` | Create tree (requires auth + limit check) |
| GET | `/api/knowledge-trees` | List user's knowledge trees (requires auth) |
| GET | `/api/knowledge-trees/{tree_id}` | Get tree by UUID (requires auth) |
| PUT | `/api/knowledge-trees/{tree_id}` | Update tree (title, description) |
| DELETE | `/api/knowledge-trees/{tree_id}` | Delete tree (cascades) |
| POST | `/api/knowledge-trees/preview` | Preview PDF/EPUB chapter structure (no storage) |
| POST | `/api/knowledge-trees/import` | Import tree from file → `{task_id}` (requires limit check) |
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

## Database schema (16 tables)

### User & Authentication
- `users`: `id` (UUID PK), `email` (UNIQUE), `password_hash`, `display_name`, `is_active`, `created_at`, `updated_at`
- `subscription_plans`: `id` (UUID PK), `slug` (UNIQUE), `name`, `description`, `max_documents`, `max_knowledge_trees`, `is_active`, `created_at`
- `user_subscriptions`: `id` (UUID PK), `user_id` (FK cascade), `plan_id` (FK), `assigned_at` — UNIQUE(user_id)

### Knowledge Tree Tables
- `knowledge_trees`: `id` (UUID PK), `user_id` (FK cascade), `title`, `description`, `created_at` — indexed by user_id
- `knowledge_chapters`: `id` (UUID PK), `tree_id` (FK cascade), `number` (1-based), `title`, `created_at` — UNIQUE(tree_id, number)
- `knowledge_documents`: `id` (UUID PK), `tree_id` (FK), `chapter_id` (nullable FK), `title`, `content`, `is_main`, `source_file_path`, `source_file_name`, `page_start`, `page_end`, `created_at`, `updated_at`
- `knowledge_content`: `id` (UUID PK), `tree_id` (FK), `chapter_id` (FK), `doc_id` (FK), `chunk_index`, `text`, `token_count`, `created_at` — UNIQUE(doc_id, chunk_index)
- `knowledge_tree_questions`: `id` (UUID PK), `tree_id` (FK), `chapter_id` (FK), `question_type` (CHECK enum), `question_data` (JSONB), `created_at`
- `flashcards`: `id` (UUID PK), `tree_id` (FK), `chapter_id` (FK), `doc_id` (nullable FK), `front`, `back`, `source_text`, `created_at`

### Task Management
- `tasks`: `id` (TEXT PK), `task_type`, `status`, `progress_pct`, `progress` (TEXT), `result` (JSONB), `error`, `created_at`, `updated_at`

## Development rules

- Domain models in `core/` must not import from `infrastructure/` or `application/`.
- Infrastructure adapters implement ports defined in `core/ports/`.
- Keep modules small and testable. No unnecessary abstractions.
- Pin Docker images to specific versions.
- Integration tests are marked `@pytest.mark.integration` and skipped if services are unreachable.
- All modules use `logging.getLogger(__name__)`; root logger configured in `api/main.py`.
- `api/` routers must use `ServicesDep` for dependency injection; never instantiate services directly inside routers.
- **Authentication required** — All knowledge tree endpoints except preview require CurrentUser (Bearer token).
- **Limit checks before write** — POST/PUT/DELETE on trees/chapters/documents check user plan limits via `check_can_create_tree()` or `check_can_create_document()`. Raise `PlanLimitExceeded` if exceeded.
- **Password hashing** — Use bcrypt (via `get_password_hash()` and `verify_password()` in `infrastructure/auth/jwt_handler.py`). Never store plaintext passwords.
- **Token expiry** — JWT tokens expire in 7 days. Frontend should handle 401 responses by redirecting to login.
- **User ownership scoping** — Routers filter knowledge trees by current_user.id before returning results. No cross-user data leakage.
- **Generation parameters** — All LLM calls accept optional GenerationParams (temperature, top_p, max_tokens). Frontend generation settings page sets these per-request.
- **Chat context** — DocumentChatAgent extracts PDF/EPUB text at client time (via extractPdfText util) and passes as `context` param. System prompt instructions to ground responses in provided context.
- **Chapter page ranges** — Knowledge documents store page_start/page_end. PDF import per-chapter slices pages based on chapter metadata.
- **Background tasks** — Tasks receive a `Task` object as first argument and write to `task.progress` / `task.progress_pct` for live status updates.
- **Frontend dev server** — Runs on port 5173; the FastAPI backend must be running independently on port 8000.
- **Question validation** — Per-type strict validation — invalid questions discarded silently (no re-prompting).

## Preflight

Validated: 2026-04-26. Run `make tools` to verify toolchain is still current.

### Toolchain

| Tool | Version | Required |
|------|---------|---------|
| python3 | 3.12.3 | >=3.12 (pyproject.toml) |
| uv | 0.10.10 | dependency manager |
| node | 24.14.0 | frontend |
| npm | 11.9.0 | frontend |
| docker | 29.2.1 | PostgreSQL |
| docker compose | v5.0.2 | orchestration |
| make | 4.3 | task runner |

All required tools present. No blockers.

### Commands

```bash
# Backend
cd backend && uv sync                  # install deps
cd backend && uv run ruff check .      # lint (check)
cd backend && uv run pytest            # unit tests (integration skipped without PostgreSQL)

# Frontend
cd frontend && npm install             # install deps
cd frontend && npm run type-check      # TypeScript check
cd frontend && npm run build           # production build (tsc + vite)
cd frontend && npm run test:run        # Vitest unit tests

# Infrastructure
docker compose up -d postgres          # start PostgreSQL only
make dev                               # full dev stack (PostgreSQL + backend + frontend)
make check                             # health check all services
```

### Known issues (from last preflighter run 2026-04-24)

- **Backend — ruff (14 errors)**: Unused imports, unsorted import block, lines >100 chars. Run `uv run ruff check --fix .` for auto-fixable ones; remaining need manual SQL string wrapping.
- **Frontend — TypeScript (5 errors)**: Unused `User` import in `sidebar.tsx`; `err.response?.data` typed as `{}` in `real-client.ts` (needs proper error-response type).
- **Frontend tests**: Vitest is configured (`vitest` script in `package.json`) but no test files exist yet.
