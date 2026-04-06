# Document Assistant

A local document reader with a web UI. Ingests PDFs and EPUBs, stores text in PostgreSQL, and uses LLM agents to summarize chapters and generate flashcards.

Uses Docker (PostgreSQL), Groq API for LLM inference (or Ollama locally), and a Vite web SPA backed by a FastAPI server.

## Features

- PDF and EPUB ingestion with structural segmentation (chapters, sections, pages)
- Two-phase ingestion: preview chapter structure → select chapters to ingest
- Text normalization: whitespace cleanup, repeated header/footer stripping
- Chapter-aware chunking with configurable token windows and overlap
- LLM agents: summarizer, flashcard generator
- Flashcard quality filtering: post-generation heuristic removes trivial cards
- Idempotent ingestion by SHA-256 file hash
- PostgreSQL persistence — raw chunks, AI-generated summaries, flashcards, and document metadata
- Task polling — background tasks return a `task_id`; frontend polls for progress (no SSE)
- FastAPI backend — REST API with background task polling
- Vite web SPA — Library, Document detail (summary / flashcards / exam tabs), Settings
- Groq as default LLM — fast inference via Groq API with built-in rate limiter; optional fast model for bulk generation tasks
- JSON retry — agents retry once with a correction prompt when the LLM returns malformed JSON

## Prerequisites

- [Groq API key](https://console.groq.com) — free, no credit card required
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+
- Node.js 18+ (for web frontend)

## Quick start

### 1. Start infrastructure services

```bash
docker compose up -d
```

This starts:
- **PostgreSQL** 17.4 on port 5432
  - Database: `docassist`, user: `docassist`, password: `docassist_pass`

### 2. Set your Groq API key

```bash
export DOCASSIST_GROQ__API_KEY=gsk_your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com). No credit card required.

### 3. Install dependencies

```bash
cd backend && uv sync
```

### 4. Verify everything works

```bash
make check
# or
cd backend && uv run python -m cli.main check
```

Expected output:
```
Service health checks:
  Groq API: OK
  PostgreSQL (localhost:5432): OK
```

### 5. Run the web app

```bash
# Recommended: start everything with make
make start

# Or manually:
# Terminal 1 — start the FastAPI backend
cd backend && uv run uvicorn api.main:app --port 8000

# Terminal 2 — start the frontend dev server
cd frontend
npm install   # first time only
npm run dev
```

The Vite dev server starts on port 5173 and proxies `/api` requests to the FastAPI backend on port 8000. Open `http://localhost:5173` in a browser.

### Alternative: API only

```bash
cd backend && uv run uvicorn api.main:app --port 8000
# then open http://localhost:8000/docs for interactive API docs
```

## Usage

### Ingest a document

```bash
cd backend && uv run python -m cli.main ingest ../data/raw/book.pdf
# or a whole directory
cd backend && uv run python -m cli.main ingest ../data/raw/
```

This will:
1. Hash the file and skip if already ingested
2. Parse and normalize pages
3. Split into chapters and chunks
4. Store chunks in PostgreSQL
5. Write `data/output/<book>/manifest.json`

### Generate chapter summary only

```bash
cd backend && uv run python -m cli.main summarize "book" 1
```

## Project structure

```
document-assistant/
├── config/
│   └── default.yml              # Service URLs, model names, chunking params
├── backend/                     # All Python backend code
│   ├── core/
│   │   ├── model/               # Document, Chapter, Page, Chunk, Summary, Flashcard, DocumentMetadata
│   │   └── ports/               # LLM, ContentStore ABCs
│   ├── application/
│   │   ├── agents/              # SummarizerAgent, FlashcardGeneratorAgent
│   │   └── ingest.py            # ingest_file() use case
│   ├── infrastructure/
│   │   ├── config.py            # Pydantic-settings config loader + save_config()
│   │   ├── ingest/              # pdf_loader, epub_loader, normalizer
│   │   ├── chunking/            # ChapterAwareSplitter
│   │   ├── llm/                 # OllamaLLM, GroqLLM, factory
│   │   ├── db/                  # PostgresPool, ContentRepository, schema + migrations
│   │   └── output/              # manifest writer
│   ├── api/                     # FastAPI backend
│   │   ├── main.py              # App factory, lifespan, CORS
│   │   ├── services.py          # Singleton service container
│   │   ├── deps.py              # FastAPI dependency injection
│   │   ├── tasks.py             # In-memory task registry + ThreadPoolExecutor
│   │   ├── routers/             # health, documents, chapters, content, config, tasks
│   │   └── schemas/             # Pydantic request/response models
│   ├── cli/
│   │   └── main.py              # CLI: check, ingest, summarize, config
│   ├── tests/
│   │   ├── integration/
│   │   └── ...
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                    # Vite web SPA (React + TypeScript + Tailwind)
│   └── src/
│       ├── pages/               # Library, Document (summary/flashcards/exam/chat), Settings
│       ├── components/          # Layout (Sidebar, Header, HealthBanner) + Shadcn-style UI
│       ├── hooks/               # useHealth, useTask, useDocuments, useDocumentStructure
│       ├── stores/              # Zustand: AppStore, DocumentStore, TaskStore, FlashcardStore, UploadStore
│       ├── services/            # API client abstraction (real / mock clients)
│       ├── types/               # TypeScript domain and API types
│       ├── lib/                 # Utilities: cn (classname)
│       └── mocks/               # Mock data for development/testing
├── docker-compose.yml           # PostgreSQL
└── data/
    ├── raw/                     # Place PDFs/EPUBs here
    └── output/                  # Manifests per document
```

## Configuration

All settings live in `config/default.yml` and can be overridden with environment variables:

```bash
# Groq API key (required — default LLM provider)
export DOCASSIST_GROQ__API_KEY=gsk_your_key_here

# Switch to local Ollama for LLM inference (optional)
export DOCASSIST_LLM_PROVIDER=ollama

# Override Ollama URL
export DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434

# Override PostgreSQL connection
export DOCASSIST_POSTGRES__HOST=db-host
```

To use Ollama for LLM inference instead of Groq (fully offline):

```bash
cd backend && uv run python -m cli.main summarize "book" 1 --provider ollama
```

## Development

```bash
# Start all services (infrastructure + backend + frontend)
make start

# Stop all services
make stop

# Run unit tests (no services required)
cd backend && uv run pytest

# Run integration tests (requires running Docker services)
cd backend && uv run pytest -m integration

# Lint Python
cd backend && uv run ruff check .

# Auto-fix lint issues
cd backend && uv run ruff check --fix .

# Build TypeScript frontend (from frontend/)
cd frontend && npm run build
```

## License

Private project.
