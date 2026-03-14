# Document Assistant — Implementation Plan

## Goal

Build a local document reader agent that:
- Ingests PDFs / EPUBs (text-focused)
- Builds a vector index (Qdrant) and a knowledge graph (Neo4j)
- Exposes a hybrid retriever (vector + keyword + metadata)
- Orchestrates LLM agents to summarize, generate questions, and write Markdown outputs per chapter
- Runs entirely locally with Docker + Ollama

## Architecture overview

```
Documents (PDF/EPUB)
    │
    ├─> Ingestion pipeline (parsers)
    ├─> Preprocessor (clean, normalize)
    ├─> Semantic chunking (token windows)
    ├─> Embeddings (Ollama)
    ├─> Vector store (Qdrant)
    ├─> Entity extraction → Knowledge Graph (Neo4j)
    │
Hybrid Retriever: vector + BM25 (Qdrant built-in) + metadata filters
    │
Context Assembler (hierarchical selection + reranker)
    │
Agent Pipeline (LLM via Ollama):
    - Summarizer
    - QA (RAG)
    - Question generator
    - Markdown writer
    │
Outputs: chapter-summary.md, chapter-questions.md, chapter-flashcards.md
```

## Progress

- [x] **Phase A** — Infra & Environment (completed)

---

## Remaining phases

### Phase B — Ingestion & Preprocessing

**Location:** `infrastructure/ingest/`, `application/ingest.py`

1. **PDF parser** (`infrastructure/ingest/pdf_loader.py`)
   - Use PyMuPDF (fitz) for text extraction
   - Extract per-page text, preserve reading order
   - Detect pages with very low text (flag for future OCR)
   - Return `Document` with `Page` objects

2. **EPUB parser** (`infrastructure/ingest/epub_loader.py`)
   - Use ebooklib to extract chapter boundaries
   - HTML → plain text via `lxml` (already a dependency)
   - Extract metadata: title, author from EPUB metadata
   - Return `Document` with `Chapter` objects

3. **Normalization** (`infrastructure/ingest/normalizer.py`)
   - Normalize whitespace, unify newlines
   - Strip repeated headers/footers (heuristic: repeated text at page start/end)
   - Detect and mark page breaks

4. **Structural segmentation**
   - Detect chapters/sections via headings (EPUB HTML tags, regex for PDFs)
   - If detection fails, create synthetic boundaries (every N pages)
   - Assign `chapter_id` and `section_id` to each segment

5. **Idempotent ingestion** (`application/ingest.py`)
   - Hash file contents (SHA-256) before processing
   - Skip files already ingested (by checking hash in Qdrant metadata)

**Tests:** sample PDF and EPUB fixtures, verify page/chapter extraction, normalization output.

---

### Phase C — Chunking

**Location:** `infrastructure/chunking/splitter.py`

1. **Sliding-window token chunker**
   - Configurable `max_tokens` (default 512) and `overlap_tokens` (default 128)
   - Token counting via simple whitespace split (upgrade to tiktoken later if needed)
   - Each chunk gets: UUID, text, token_count, `ChunkMetadata` (source, chapter, page, char offsets)

2. **Chapter-aware splitting**
   - Never split a chunk across chapter boundaries
   - Preserve chapter/section context in metadata

**Tests:** verify chunk sizes, overlap correctness, boundary handling.

---

### Phase D — Embeddings

**Location:** `infrastructure/llm/ollama.py` (extend existing), `core/ports/embedder.py` (implement)

1. **Ollama embedder adapter**
   - Implement `Embedder` port using Ollama's `/api/embed` endpoint
   - Batch embedding support
   - Model: `nomic-embed-text` (768-dim)

2. **Embedding cache**
   - Cache embeddings by chunk hash to avoid re-embedding unchanged text
   - Simple file-based or SQLite cache

**Tests:** mock Ollama responses, verify vector dimensions, batch handling.

---

### Phase E — Vector Store (Qdrant)

**Location:** `infrastructure/vectorstore/qdrant_store.py`

1. **Collection setup**
   - Create collection with vector size matching embedding model
   - Distance: Cosine
   - Enable built-in full-text index on `text` field (for BM25 keyword search)
   - Payload indexes on: `book` (keyword), `chapter` (integer), `page` (integer), `file_hash` (keyword)

2. **Upsert pipeline**
   - Batch upsert (256–1024 points per call)
   - Payload: text, book, chapter, section, page, source file, chunk hash

3. **Search interface**
   - Vector similarity search with optional metadata filters
   - Full-text search (BM25) via Qdrant's built-in text index
   - Combined hybrid search: merge vector + keyword results

**Tests:** integration tests against running Qdrant (skip if unavailable).

---

### Phase F — Knowledge Graph (Neo4j)

**Location:** `infrastructure/graph/neo4j_store.py`, `infrastructure/graph/entity_extractor.py`

1. **Entity extraction** (LLM-based, not spaCy)
   - Prompt Ollama to extract entities (people, places, organizations, concepts, events) from chunks
   - Parse structured output (JSON) from LLM response
   - Fallback: regex patterns for common entity types

2. **Graph schema**
   - Node types: `Entity` (labeled: Person/Place/Organization/Event/Concept), `Document`, `Chapter`
   - Relationship types: `MENTIONS`, `APPEARS_IN`, `RELATES_TO`, `CAUSES`, `LOCATED_IN`
   - Provenance on every edge: `{source_file, chapter, page, chunk_id}`

3. **Batch loading**
   - Use neo4j driver with batched MERGE operations
   - Create indexes on `Entity.name` and `Entity.label`

**Tests:** integration tests against running Neo4j, verify node/edge creation.

---

### Phase G — Hybrid Retriever & Reranker

**Location:** `application/retriever.py`, `infrastructure/reranker/`

1. **Retrieval pipeline** for a query:
   - Embed query → vector top-K (Qdrant, k=20)
   - Keyword search (Qdrant full-text, top-M)
   - Optionally: graph traversal for entity-related chunks
   - Merge and deduplicate result sets

2. **Reranker** (LLM-based)
   - Prompt Ollama to rank candidate passages by relevance to query
   - No cross-encoder model needed initially

3. **Context assembly**
   - Prefer chapter summaries first, then top micro-chunks
   - Respect token budget (configurable, default ~6K tokens)
   - Apply metadata filters when user specifies (chapter, book, page range)

---

### Phase H — Agent Layer

**Location:** `application/agents/`

Direct Ollama calls, no LlamaIndex/LangChain.

1. **Summarizer agent** — chapter/section summaries, stored as text + embeddings
2. **QA agent** — answers queries via hybrid retriever → context assembly → LLM
3. **Question generator** — given chapter context, generates study questions with answers
4. **Markdown writer** — formats agent output into structured `.md` files

**Prompting patterns:**
- System prompt enforcing context-only answers
- Explicit output format (fenced Markdown or JSON)
- Structured parsing of LLM output

---

### Phase I — Markdown Output

**Location:** `infrastructure/output/markdown_writer.py`

1. **Output templates:**
   - `chapter{n}-summary.md`
   - `chapter{n}-questions.md`
   - `chapter{n}-flashcards.md`

2. **Layout:**
   ```markdown
   # Chapter N — Title
   **Source:** book.pdf (pages X-Y)
   ## Summary
   - bullet points
   ## Questions
   1. Q — A
   ## References
   ```

3. **Provenance:** embed source page/chunk references in each item

---

### Phase J — CLI

**Location:** `cli/main.py` (extend existing)

1. **Commands:**
   - `ingest [file|dir]` — process and index documents
   - `summarize <book> <chapter>` — generate chapter summary
   - `ask --query "..." [--book ...] [--chapter ...]` — RAG question answering
   - `generate-md <book> <chapter>` — produce all Markdown outputs

2. **HTTP API** (deferred, add only if CLI proves insufficient)

---

### Phase K — Testing & Evaluation

1. Unit tests for ingestion, chunking, normalization
2. Integration tests for Qdrant and Neo4j pipelines
3. Retrieval recall evaluation: given sample QA pairs, measure top-K hit rate
4. Manual correctness checks for generated summaries and questions

---

### Phase L — Monitoring & Maintenance

1. Structured logging (ingestion, upserts, queries, errors)
2. Metrics: retrieval latency, model latency, queries per session
3. Reindexing strategy for embedding model changes
4. Ingestion manifests: model versions, collection settings, timestamps

---

## Operational notes

- Reproducibility: store a manifest per ingestion run
- Security: all services local-only, Neo4j password-protected
- Batch all Qdrant upserts and embedding calls
- Use quantized Ollama models (GGUF/4-bit) to reduce resource usage

## Future extensions

- Cross-document summarizer (book-level TL;DRs)
- Multi-document comparators (compare chapters across books)
- Knowledge graph visualizations (interactive)
- Web UI for browsing passages and graph views
- Active learning: surface low-confidence items for human review

---

## Observations — Changes from original plan

The following items from the original plan (`future_document_agent_plan.txt`) were intentionally changed or deferred during the Phase A review:

### Dropped

1. **LlamaIndex / LangChain** — Replaced with direct `requests` calls to Ollama + native `qdrant-client` + `neo4j` driver. These frameworks add massive dependency trees for what is fundamentally: call Ollama, query Qdrant, assemble prompt. Direct calls are simpler and more debuggable.

2. **Whoosh** — Removed entirely. Qdrant v1.7+ supports built-in full-text search, which covers BM25-style keyword search without an extra dependency.

3. **`requirements.txt` + pip + venv** — Replaced with `uv` + `pyproject.toml`. Faster installs, better dependency resolution, single tool for env management.

4. **Flat `src/` layout** — Restructured to `core/` / `application/` / `infrastructure/` layered architecture per project preferences (DDD-inspired).

5. **`version: "3.8"` in docker-compose** — Removed. The `version` key is deprecated in modern Docker Compose. Services use named volumes instead of bind mounts.

6. **Unpinned Docker images** (`qdrant/qdrant:latest`) — Pinned to specific versions (`qdrant/qdrant:v1.13.2`) for reproducibility.

### Deferred

1. **spaCy NER** — Deferred to Phase F. Will start with LLM-based entity extraction via Ollama instead. Add spaCy only if extraction quality or speed is insufficient.

2. **Tesseract OCR** — Deferred indefinitely. Most text PDFs/EPUBs don't need it. Will add when encountering scanned documents.

3. **HTTP API** — Deferred. CLI-first approach. Add API only if the CLI proves insufficient for the workflow.

4. **tiktoken / sentencepiece / transformers** — Not included as dependencies. Simple whitespace-based token counting is sufficient initially. Can add tiktoken later if precise counting is needed.

### Added (not in original plan)

1. **pydantic-settings config** — Central YAML config (`config/default.yml`) with pydantic validation and environment variable overrides. The original plan had no configuration management.

2. **Health checks in Docker Compose** — Both Qdrant and Neo4j containers have proper health checks with start periods and retry logic.

3. **Idempotent ingestion by file hash** — `Document` model includes `file_hash` field. Ingestion pipeline will skip already-processed files.

4. **Port/adapter pattern** — `core/ports/` defines ABCs (`Embedder`, `LLM`) that infrastructure adapters implement. This keeps domain logic decoupled from external services.

5. **CLI `check` command** — Verifies connectivity to all three services (Ollama, Qdrant, Neo4j) with clear pass/fail output. Not in the original plan.
