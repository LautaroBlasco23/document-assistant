# Document Assistant

A local document reader with a desktop UI. Ingests PDFs and EPUBs, builds a vector index and knowledge graph, and uses LLM agents to summarize chapters, generate study questions, and answer questions with hybrid retrieval.

Runs entirely locally: Docker (Qdrant + Neo4j), Ollama for LLM inference, and an Electron desktop app backed by a FastAPI server.

## Features

- PDF and EPUB ingestion with structural segmentation (chapters, sections, pages)
- Text normalization: whitespace cleanup, repeated header/footer stripping
- Chapter-aware chunking with configurable token windows and overlap
- Vector search via Qdrant (cosine similarity + full-text BM25)
- Knowledge graph via Neo4j: LLM-extracted entities with regex fallback
- Hybrid retrieval: vector + keyword + graph traversal + LLM reranker
- LLM agents: summarizer, QA, question generator
- Markdown output: per-chapter summary, study questions, flashcards
- Idempotent ingestion by SHA-256 file hash
- SQLite embedding cache to avoid re-embedding unchanged text
- Ingestion manifest (JSON) per book with model/collection/timestamp metadata
- **FastAPI backend** — REST API with SSE streaming for Q&A and background task polling
- **Electron desktop UI** — 6 screens: Dashboard, Documents, Search, Ask, Chapter Analysis, Settings

## Prerequisites

- [Ollama](https://ollama.ai) installed on host
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+
- Node.js 18+ (for Electron UI)

## Quick start

### 1. Start infrastructure services

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts:
- **Qdrant** (v1.13.2) on ports 6333/6334
- **Neo4j** 5 on ports 7474 (browser) / 7687 (bolt)
  - Default credentials: `neo4j` / `document_assistant_pass`

### 2. Pull Ollama models

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Verify everything works

```bash
uv run python -m cli.main check
```

Expected output:
```
Service health checks:
  Ollama (http://localhost:11434): OK
  Qdrant (http://localhost:6333): OK
  Neo4j  (bolt://localhost:7687): OK
```

### 5. Run the desktop app

```bash
cd electron
npm install
npm run dev
```

Electron will start, spawn the FastAPI server on port 8000, and open the UI once the backend is healthy.

### Alternative: API only (no Electron)

```bash
uv run uvicorn api.main:app --port 8000
# then open http://localhost:8000/docs for interactive API docs
```

## Usage

### Ingest a document

```bash
uv run python -m cli.main ingest data/raw/book.pdf
# or a whole directory
uv run python -m cli.main ingest data/raw/
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
uv run python -m cli.main generate-md "book" 1
```

Produces in `data/output/<book>/`:
- `chapter1-summary.md`
- `chapter1-questions.md`
- `chapter1-flashcards.md`

### Ask a question

```bash
uv run python -m cli.main ask "What is the main argument?"
uv run python -m cli.main ask "Who is the protagonist?" --book "book"
uv run python -m cli.main ask "Explain the key concept" --book "book" --chapter 3
```

### Generate chapter summary only

```bash
uv run python -m cli.main summarize "book" 1
```

## Project structure

```
document-assistant/
├── config/
│   └── default.yml              # Service URLs, model names, chunking params
├── core/
│   ├── model/
│   │   ├── document.py          # Document, Chapter, Page
│   │   └── chunk.py             # Chunk, ChunkMetadata
│   └── ports/
│       ├── embedder.py          # Embedder ABC
│       └── llm.py               # LLM ABC
├── application/
│   ├── agents/
│   │   ├── base.py              # BaseAgent
│   │   ├── summarizer.py        # SummarizerAgent
│   │   ├── qa_agent.py          # QAAgent
│   │   └── question_generator.py # QuestionGeneratorAgent
│   ├── ingest.py                # ingest_file() use case
│   └── retriever.py             # HybridRetriever
├── infrastructure/
│   ├── config.py                # Pydantic-settings config loader
│   ├── ingest/
│   │   ├── pdf_loader.py        # PyMuPDF-based PDF parser
│   │   ├── epub_loader.py       # ebooklib + lxml EPUB parser
│   │   └── normalizer.py        # Whitespace + header/footer normalization
│   ├── chunking/
│   │   └── splitter.py          # ChapterAwareSplitter (sliding window)
│   ├── llm/
│   │   ├── ollama.py            # OllamaClient, OllamaEmbedder, OllamaLLM
│   │   └── embedding_cache.py   # SQLite embedding cache
│   ├── vectorstore/
│   │   └── qdrant_store.py      # QdrantStore (upsert, vector/text search)
│   ├── graph/
│   │   ├── neo4j_store.py       # Neo4jStore (entity upsert, graph queries)
│   │   └── entity_extractor.py  # LLM entity extraction + regex fallback
│   └── output/
│       ├── markdown_writer.py   # write_summary / write_questions / write_flashcards
│       └── manifest.py          # write_manifest (JSON ingestion record)
├── cli/
│   └── main.py                  # CLI: check, ingest, summarize, ask, generate-md
├── docker/
│   └── docker-compose.yml       # Qdrant + Neo4j
├── tests/
│   ├── ingest/                  # Normalizer + PDF loader unit tests
│   ├── chunking/                # Splitter unit tests
│   ├── embeddings/              # OllamaEmbedder + cache unit tests
│   ├── integration/             # Qdrant + Neo4j integration tests (skipped if down)
│   └── eval/
│       └── sample_qa.json       # Retrieval evaluation pairs
└── data/
    ├── raw/                     # Place PDFs/EPUBs here
    ├── output/                  # Generated Markdown + manifests
    └── .cache/                  # SQLite embedding cache
```

## Configuration

All settings live in `config/default.yml` and can be overridden with environment variables:

```bash
export DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434
export DOCASSIST_OLLAMA__GENERATION_MODEL=mistral
export DOCASSIST_QDRANT__COLLECTION_NAME=my_docs
```

## Development

```bash
# Run unit tests (no services required)
uv run pytest

# Run integration tests (requires running Docker services)
uv run pytest -m integration

# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .
```

## License

Private project.
