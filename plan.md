# Document Assistant — Implementation Plan

## Goal

Build a local document reader agent that:
- Ingests PDFs / EPUBs (text-focused)
- Builds a vector index (Qdrant) and a knowledge graph (Neo4j)
- Exposes a hybrid retriever (vector + keyword + graph + LLM reranker)
- Orchestrates LLM agents to summarize, generate questions, and write Markdown outputs per chapter
- Runs entirely locally with Docker + Ollama

## Architecture overview

```
Documents (PDF/EPUB)
    │
    ├─> Ingestion pipeline (pdf_loader, epub_loader)
    ├─> Normalizer (whitespace, header/footer stripping)
    ├─> ChapterAwareSplitter (sliding window, no chapter crossing)
    ├─> OllamaEmbedder (nomic-embed-text, SQLite cache)
    ├─> QdrantStore (cosine + full-text index)
    ├─> Entity extraction → Neo4jStore
    │
HybridRetriever: vector + BM25 (Qdrant built-in) + graph + LLM rerank
    │
Token budget trim (default 6000 tokens)
    │
Agent Pipeline (OllamaLLM via /api/chat):
    - SummarizerAgent
    - QAAgent
    - QuestionGeneratorAgent
    │
Outputs: chapter-summary.md, chapter-questions.md, chapter-flashcards.md
         manifest.json (per book)
```

## Progress

- [x] **Phase A** — Infra & Environment
- [x] **Phase B** — Ingestion & Preprocessing
- [x] **Phase C** — Chunking
- [x] **Phase D** — Embeddings
- [x] **Phase E** — Vector Store (Qdrant)
- [x] **Phase F** — Knowledge Graph (Neo4j)
- [x] **Phase G** — Hybrid Retriever & Reranker
- [x] **Phase H** — Agent Layer
- [x] **Phase I** — Markdown Output
- [x] **Phase J** — CLI Extensions
- [x] **Phase K** — Testing & Evaluation
- [x] **Phase L** — Monitoring & Maintenance

---

## Phases (completed)

### Phase A — Infra & Environment ✓

- Domain models: `Document`, `Chapter`, `Page`, `Chunk`, `ChunkMetadata`
- Port ABCs: `Embedder`, `LLM`
- Pydantic config (`AppConfig`) with YAML + env var overrides
- `OllamaClient` (health check, model listing)
- `cli check` command
- Docker Compose: Qdrant v1.13.2, Neo4j 5

### Phase B — Ingestion & Preprocessing ✓

- `infrastructure/ingest/pdf_loader.py` — PyMuPDF, chapter detection via regex, synthetic fallback (every 20 pages)
- `infrastructure/ingest/epub_loader.py` — ebooklib + lxml, spine item → Chapter, EPUB metadata
- `infrastructure/ingest/normalizer.py` — whitespace collapse, header/footer stripping (>30% page threshold)
- `application/ingest.py` — SHA-256 hash, Qdrant idempotency check, loader dispatch

### Phase C — Chunking ✓

- `infrastructure/chunking/splitter.py` — `ChapterAwareSplitter(max_tokens, overlap_tokens)`
- Sliding window within each chapter; never crosses chapter boundary
- Token count = `len(text.split())`

### Phase D — Embeddings ✓

- `infrastructure/llm/ollama.py` — `OllamaEmbedder` (POST `/api/embed`, batch 32) + `OllamaLLM` (POST `/api/generate` + `/api/chat`)
- `infrastructure/llm/embedding_cache.py` — SQLite cache at `data/.cache/embeddings.db`, keyed by SHA-256 of text

### Phase E — Vector Store ✓

- `infrastructure/vectorstore/qdrant_store.py` — `QdrantStore`
- `ensure_collection`: cosine distance, payload indexes (book, chapter, page, file_hash), full-text index on `text`
- `upsert` (batch 512), `search_vector`, `search_text`, `has_file`, `fetch_by_ids`

### Phase F — Knowledge Graph ✓

- `infrastructure/graph/entity_extractor.py` — LLM JSON extraction + regex fallback (capitalized bigrams)
- `infrastructure/graph/neo4j_store.py` — `Neo4jStore`: MERGE-based entity upsert, `MENTIONS` relationships, `query_related`

### Phase G — Hybrid Retriever & Reranker ✓

- `application/retriever.py` — `HybridRetriever`
- Pipeline: embed query → vector top-20 → keyword top-20 → graph entity lookup → deduplicate → LLM rerank → token budget trim (6000)

### Phase H — Agent Layer ✓

- `application/agents/base.py` — `BaseAgent._call(system, user)`
- `application/agents/summarizer.py` — `SummarizerAgent.summarize(chapter, chunks)`
- `application/agents/qa_agent.py` — `QAAgent.answer(query, chunks)`
- `application/agents/question_generator.py` — `QuestionGeneratorAgent.generate(chunks)` → `list[{question, answer}]`

### Phase I — Markdown Output ✓

- `infrastructure/output/markdown_writer.py` — `write_summary`, `write_questions`, `write_flashcards`
- Output path: `data/output/{book_title}/chapter{n}-{type}.md`
- `infrastructure/output/manifest.py` — `write_manifest` → `data/output/{book_title}/manifest.json`

### Phase J — CLI Extensions ✓

- `cli/main.py` extended with: `ingest`, `summarize`, `ask`, `generate-md`
- `--log-format text|json` flag; logging configured at startup
- Progress output to stdout; errors to stderr; exit codes

### Phase K — Testing & Evaluation ✓

- `tests/ingest/` — normalizer + PDF loader unit tests (fixture PDFs built in-memory with PyMuPDF)
- `tests/chunking/` — size, overlap, chapter boundary, empty doc, metadata tests
- `tests/embeddings/` — cache hit/miss/overwrite; embedder dimensions, caching, batching (mocked HTTP)
- `tests/integration/` — `@pytest.mark.integration` for Qdrant + Neo4j (auto-skipped if unreachable)
- `tests/eval/sample_qa.json` — 5 retrieval evaluation pairs

### Phase L — Monitoring & Maintenance ✓

- `logging.getLogger(__name__)` in every module
- `time.perf_counter` timing logged during ingest
- Root logger configured in `cli/main.py`: text or JSON format via `--log-format`
- `manifest.json` written after each successful ingest: `{file_hash, title, model, collection, timestamp, chunk_count}`

---

## Operational notes

- Reproducibility: manifest per ingestion run records model + collection + timestamp
- Security: all services local-only; Neo4j password-protected
- Batch all Qdrant upserts (512 points) and embedding calls (32 texts)
- Use quantized Ollama models (GGUF/4-bit) to reduce resource usage

## Future extensions

- Cross-document summarizer (book-level TL;DRs)
- Multi-document comparators (compare chapters across books)
- Knowledge graph visualizations (interactive)
- Web UI for browsing passages and graph views
- spaCy NER if LLM extraction quality is insufficient
- Tesseract OCR for scanned documents
- tiktoken for precise token counting
- HTTP API if CLI proves insufficient

---

## Key decisions log

### Dropped from original plan

1. **LlamaIndex / LangChain** — Direct `requests` to Ollama + native clients. Simpler, more debuggable.
2. **Whoosh** — Qdrant v1.7+ built-in full-text search covers BM25 keyword search.
3. **`requirements.txt` + pip + venv** — Replaced with `uv` + `pyproject.toml`.
4. **Flat `src/` layout** — DDD-inspired `core/` / `application/` / `infrastructure/` layering.
5. **`version: "3.8"` in docker-compose** — Deprecated; removed.
6. **Unpinned Docker images** — Pinned to specific versions for reproducibility.

### Deferred

1. **spaCy NER** — Using LLM-based extraction + regex fallback.
2. **Tesseract OCR** — Not needed for text PDFs/EPUBs.
3. **HTTP API** — CLI-first approach.
4. **tiktoken** — Whitespace split is sufficient initially.

### Added

1. **Pydantic-settings config** — Central YAML + env var overrides.
2. **Health checks in Docker Compose** — Proper start periods and retry logic.
3. **Idempotent ingestion by file hash** — SHA-256 + Qdrant check before processing.
4. **Port/adapter pattern** — `Embedder` and `LLM` ABCs in `core/ports/`.
5. **SQLite embedding cache** — Avoids re-embedding unchanged chunks across runs.
6. **LLM reranker** — Sorts candidate chunks by relevance before context assembly.
