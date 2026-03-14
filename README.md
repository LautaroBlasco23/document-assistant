# Document Assistant

A local document reader agent that ingests PDFs and EPUBs, builds a vector index and knowledge graph, and uses LLM agents to summarize, generate questions, and produce structured Markdown outputs per chapter.

Runs entirely locally using Docker services and Ollama for LLM inference.

## Features (planned)

- PDF and EPUB ingestion with structural segmentation (chapters, sections, pages)
- Semantic chunking with configurable token windows
- Vector search via Qdrant with metadata filtering
- Knowledge graph via Neo4j for entity/relation queries
- Hybrid retrieval (vector + keyword + graph)
- LLM-powered agents: summarizer, QA, question generator, Markdown writer
- CLI interface for all operations

## Prerequisites

- [Ollama](https://ollama.ai) installed on host
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+

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
├── application/                 # Use cases (coming soon)
├── infrastructure/
│   ├── config.py                # Pydantic-settings config loader
│   └── llm/
│       └── ollama.py            # Ollama client (health check, model listing)
├── cli/
│   └── main.py                  # CLI entry point
├── docker/
│   └── docker-compose.yml       # Qdrant + Neo4j
├── tests/
├── data/
│   ├── raw/                     # Place PDFs/EPUBs here
│   └── output/                  # Generated Markdown outputs
└── pyproject.toml
```

## Configuration

All settings live in `config/default.yml` and can be overridden with environment variables using the prefix `DOCASSIST_` and double-underscore nesting:

```bash
export DOCASSIST_OLLAMA__BASE_URL=http://other-host:11434
export DOCASSIST_OLLAMA__GENERATION_MODEL=mistral
```

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .
```

## License

Private project.
