# Document Assistant

A knowledge tree platform for structured learning from documents. Import PDFs and EPUBs as knowledge trees, then generate summaries, flashcards, and exam questions to master the content.

Uses Docker (PostgreSQL), Groq API for LLM inference (or Ollama locally), and a Vite web SPA backed by a FastAPI server.

## Features

- **Knowledge Trees** — hierarchical learning containers: Tree → Chapters → Documents → Chunks
- **Import PDFs/EPUBs** as knowledge trees; preview structure and select specific chapters before ingesting
- **Chapter-aware chunking** with configurable token windows and overlap
- **LLM agents**: summarizer, flashcard generator, question generator
- **Four question types**: True/False, Multiple Choice, Matching, Checkbox
- **Spaced-repetition exam system** with level progression (None → Completed → Gold → Platinum)
- **Exam cooldowns** per level to encourage spaced learning
- **Flashcard quality filtering**: post-generation heuristic removes trivial cards
- **Idempotent ingestion** by SHA-256 file hash
- **PostgreSQL persistence** — chunks, summaries, flashcards, questions, exam results, and document metadata
- **Task polling** — background tasks return a `task_id`; frontend polls for progress (no SSE)
- **Multi-provider support** — Groq, Ollama, OpenRouter, and HuggingFace Inference Endpoints via `config/default.yml`
- **JSON retry** — agents retry once with a correction prompt when the LLM returns malformed JSON
- **Prompts centralized** in `backend/application/prompts.py`

## Technologies

| Tool / Runtime | Version | Role |
|----------------|---------|------|
| Python | 3.12+ | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | 0.10+ | Python dependency manager |
| FastAPI | 0.111+ | REST API server |
| PostgreSQL | 17.4 | Primary persistence |
| Node.js | 18+ | Frontend runtime |
| npm | — | Frontend dependency manager |
| React + TypeScript | 18 / 5 | SPA frontend |
| Vite | 6 | Frontend build tool |
| Docker + Compose | — | Infrastructure orchestration |
| make | — | Task runner |
| Groq API | — | Default LLM inference (free tier) |
| Ollama | — | Optional local LLM |

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

### Create a knowledge tree

1. Open the web app at `http://localhost:5173`
2. Click **Create Knowledge Tree** in the Library
3. Give it a title (e.g., "Machine Learning Fundamentals")
4. Optionally add a tree-level overview document

### Import a document

1. Open a knowledge tree
2. Click **Import Document** in the sidebar
3. Upload a PDF or EPUB — the app shows a preview of detected chapters
4. Select the chapters to import and confirm
5. Background task parses, chunks, and stores the content

### Generate summaries

Open a chapter's **Content** tab → click **Summarize**. Summary is stored in PostgreSQL.

### Generate flashcards

Open a chapter's **Content** tab → click **Generate Flashcards**.

### Generate exam questions

Open a chapter's **Content** tab → click **Generate Questions**. Four question types are generated:
- **True/False** — plausible false statements require careful reading
- **Multiple Choice** — exactly 4 choices, no "all of the above" tricks
- **Matching** — terms matched to definitions
- **Checkbox** — select all correct answers

### Take an exam

1. Open a chapter's **Exam** tab
2. Questions are shuffled and filtered by type
3. Answer all questions and submit
4. **100% correct required to pass** — wrong answers are shown after submission
5. Passing increments your level for that chapter; failing triggers a cooldown

### Level progression

| Level | Name | Exams passed | Cooldown after passing |
|-------|------|-------------|----------------------|
| 0 | None | 0 | — |
| 1 | Completed | 1 | 4 days |
| 2 | Gold | 2 | 14 days |
| 3 | Platinum | 3+ | 30 days |

Failed exams do not reduce your level but trigger a **2-hour cooldown** before the next attempt.

## Project structure

```
document-assistant/
├── config/
│   └── default.yml              # Service URLs, model names, chunking params, exam cooldowns
├── backend/                     # All Python backend code
│   ├── core/
│   │   ├── model/               # Document, Chapter, Chunk, Summary, Flashcard, Question, ExamResult
│   │   └── ports/               # LLM, ContentStore, KnowledgeTreeStore ABCs
│   ├── application/
│   │   ├── agents/              # SummarizerAgent, FlashcardGeneratorAgent, QuestionGeneratorAgent
│   │   ├── prompts.py           # All agent system prompts
│   │   └── ingest.py            # Ingest use case
│   ├── infrastructure/
│   │   ├── config.py            # Pydantic-settings config loader
│   │   ├── ingest/              # pdf_loader, epub_loader, normalizer
│   │   ├── chunking/            # ChapterAwareSplitter
│   │   ├── llm/                 # OllamaLLM, GroqLLM, factory
│   │   ├── db/                  # PostgresPool, repositories, schema + migrations
│   │   └── output/              # Manifest writer
│   ├── api/
│   │   ├── main.py              # App factory, lifespan, CORS
│   │   ├── services.py          # Singleton service container
│   │   ├── deps.py              # FastAPI dependency injection
│   │   ├── tasks.py             # In-memory task registry + ThreadPoolExecutor
│   │   ├── routers/             # health, documents, knowledge_trees, exams, tasks
│   │   └── schemas/             # Pydantic request/response models
│   ├── cli/
│   │   └── main.py              # CLI: check, ingest, summarize, config
│   ├── tests/
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                    # Vite web SPA (React + TypeScript + Tailwind)
│   └── src/
│       ├── pages/
│       │   ├── library/         # Knowledge tree list, create/edit/import dialogs
│       │   ├── knowledge-tree/  # Tree detail: documents, content, exam tabs
│       │   ├── document/        # Legacy document pages (flashcards, exam, summary tabs)
│       │   └── settings/        # LLM provider config
│       ├── components/         # Layout, UI primitives (Shadcn-style)
│       ├── hooks/               # useHealth, useTask, useKnowledgeTree, etc.
│       ├── stores/              # Zustand: AppStore, KnowledgeTreeStore, ExamStore, etc.
│       ├── services/            # API client (real / mock via VITE_MOCK)
│       ├── types/               # TypeScript domain and API types
│       └── mocks/               # Mock data for development
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

The config file (`config/default.yml`) also defines which models to use per provider.

### LLM models and prompts

All LLM models are configured in `config/default.yml` under the provider sections (`groq`, `ollama`, `openrouter`, `huggingface`). Each provider has a **main model** for quality and a **fast model** for bulk generation tasks.

| Provider | Main model | Fast model |
|----------|-----------|------------|
| Groq | `llama-3.3-70b-versatile` | `llama-3.1-8b-instant` |
| Ollama | `qwen2.5:14b-instruct` | `qwen2.5:3b-instruct` |
| OpenRouter | `qwen/qwen3-next-80b-a3b-instruct:free` | `liquid/lfm-2.5-1.2b-thinking:free` |
| HuggingFace | `mistralai/Mistral-7B-Instruct-v0.3` | — |

Agent system prompts live in `backend/application/prompts.py`:
- `SUMMARY_SYSTEM` / `SUMMARY_SYSTEM_COMBINE` / `SUMMARY_SYSTEM_PARTIAL` — summarizer
- `FLASHCARDS_SYSTEM` — flashcard generator
- `QUESTIONS_TRUE_FALSE` / `QUESTIONS_MULTIPLE_CHOICE` / `QUESTIONS_MATCHING` / `QUESTIONS_CHECKBOX` — question generator

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
