# Document Assistant

A local document reader with a web UI. Ingests PDFs and EPUBs, builds a vector index and knowledge graph, and uses LLM agents to summarize chapters and generate flashcards with hybrid retrieval.

Uses Docker (Qdrant + Neo4j + PostgreSQL), Ollama for embeddings, Groq API for LLM inference, and a Vite web SPA backed by a FastAPI server.

## Features

- PDF and EPUB ingestion with structural segmentation (chapters, sections, pages)
- Text normalization: whitespace cleanup, repeated header/footer stripping
- Chapter-aware chunking with configurable token windows and overlap
- Vector search via Qdrant (cosine similarity + full-text BM25)
- Knowledge graph via Neo4j: LLM-extracted entities with regex fallback
- Hybrid retrieval: vector + keyword + graph traversal + LLM reranker
- LLM agents: summarizer, flashcard generator
- Markdown output: per-chapter summary, flashcards
- Idempotent ingestion by SHA-256 file hash
- SQLite embedding cache to avoid re-embedding unchanged text
- Ingestion manifest (JSON) per book with model/collection/timestamp metadata
- **PostgreSQL persistence** — AI-generated summaries, flashcards, and document metadata stored in PostgreSQL with idempotent schema migrations
- **Task polling** — Background tasks return a `task_id`; frontend polls for progress (no SSE)
- **FastAPI backend** — REST API with background task polling
- **Vite web SPA** — 3 pages: Library, Document detail (summary / flashcards tabs), Settings
- **Groq as default LLM** — Fast inference via Groq API with built-in rate limiter; optional fast model for bulk generation tasks
- **Flashcard quality filtering** — Post-generation heuristic filter removes trivial, short, or self-evident cards without an extra LLM call
- **Improved generation prompts** — Flashcard and summary prompts include explicit SKIP/FOCUS/SELF-CHECK rules to steer models toward meaningful, non-trivial content
- **JSON retry** — Agents retry once with a correction prompt when the LLM returns malformed JSON, improving reliability with smaller/free models

## Prerequisites

- [Groq API key](https://console.groq.com) — free, no credit card required
- [Ollama](https://ollama.ai) installed on host (for embeddings only)
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
- **Qdrant** (v1.13.2) on ports 6333/6334
- **Neo4j** 5 on ports 7474 (browser) / 7687 (bolt)
  - Default credentials: `neo4j` / `document_assistant_pass`
- **PostgreSQL** 17.4 on port 5432
  - Database: `docassist`, user: `docassist`, password: `docassist_pass`

### 2. Set your Groq API key

```bash
export DOCASSIST_GROQ__API_KEY=gsk_your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com). No credit card required.

### 3. Pull the Ollama embedding model

```bash
ollama pull nomic-embed-text
```

Ollama is used for embeddings only. LLM inference runs via Groq by default.

### 4. Install dependencies

```bash
cd backend && uv sync
```

### 5. Verify everything works

```bash
make check
# or
cd backend && uv run python -m cli.main check
```

Expected output:
```
Service health checks:
  Ollama (http://localhost:11434): OK
  Qdrant (http://localhost:6333): OK
  Neo4j  (bolt://localhost:7687): OK
```

### 6. Run the web app

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
4. Embed chunks (with SQLite cache)
5. Upsert vectors into Qdrant
6. Extract entities and store in Neo4j
7. Write `data/output/<book>/manifest.json`

### Generate Markdown outputs

```bash
cd backend && uv run python -m cli.main generate-md "book" 1
```

Produces in `data/output/<book>/`:
- `chapter1-summary.md`
- `chapter1-flashcards.md`

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
│   │   └── ports/               # Embedder, LLM, ContentStore ABCs
│   ├── application/
│   │   ├── agents/              # SummarizerAgent, FlashcardGeneratorAgent
│   │   ├── ingest.py            # ingest_file() use case
│   │   └── retriever.py         # HybridRetriever
│   ├── infrastructure/
│   │   ├── config.py            # Pydantic-settings config loader + save_config()
│   │   ├── ingest/              # pdf_loader, epub_loader, normalizer
│   │   ├── chunking/            # ChapterAwareSplitter
│   │   ├── llm/                 # OllamaEmbedder, OllamaLLM, GroqLLM, EmbeddingCache, factory
│   │   ├── vectorstore/         # QdrantStore (upsert, search, delete)
│   │   ├── graph/               # Neo4jStore (entity upsert, graph queries, delete)
│   │   ├── db/                  # PostgresPool, ContentRepository, schema + migrations
│   │   └── output/              # markdown_writer, manifest
│   ├── api/                     # FastAPI backend
│   │   ├── main.py              # App factory, lifespan, CORS
│   │   ├── services.py          # Singleton service container
│   │   ├── deps.py              # FastAPI dependency injection
│   │   ├── tasks.py             # In-memory task registry + ThreadPoolExecutor
│   │   ├── routers/             # health, documents, chapters, content, config, tasks
│   │   └── schemas/             # Pydantic request/response models
│   ├── cli/
│   │   └── main.py              # CLI: check, ingest, summarize, generate-md
│   ├── tests/
│   │   ├── ingest/
│   │   ├── chunking/
│   │   ├── embeddings/
│   │   ├── integration/
│   │   └── eval/
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                    # Vite web SPA (React + TypeScript + Tailwind)
│   └── src/
│       ├── pages/               # Library, Document (summary/flashcards), Settings
│       ├── components/          # Layout (Sidebar, Header, HealthBanner) + Shadcn-style UI
│       ├── hooks/               # useHealth, useTask, useDocuments, useDocumentStructure
│       ├── stores/              # Zustand: AppStore, DocumentStore, TaskStore, FlashcardStore, UploadStore
│       ├── services/            # API client abstraction (real / mock clients)
│       ├── types/               # TypeScript domain and API types
│       ├── lib/                 # Utilities: cn (classname)
│       └── mocks/               # Mock data for development/testing
├── docker-compose.yml           # Qdrant + Neo4j + PostgreSQL
└── data/
    ├── raw/                     # Place PDFs/EPUBs here
    ├── output/                  # Generated Markdown + manifests
    └── .cache/                  # SQLite embedding cache
```

## Configuration

All settings live in `config/default.yml` and can be overridden with environment variables:

```bash
# Groq API key (required — default LLM provider)
export DOCASSIST_GROQ__API_KEY=gsk_your_key_here

# Switch to local Ollama for LLM inference (optional)
export DOCASSIST_LLM_PROVIDER=ollama

# Override Ollama URL (used for embeddings)
export DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434

# Override PostgreSQL connection
export DOCASSIST_POSTGRES__HOST=db-host

export DOCASSIST_QDRANT__COLLECTION_NAME=my_docs
```

To use Ollama for LLM inference instead of Groq (e.g. fully offline):

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
