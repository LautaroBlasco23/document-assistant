# Knowledge Tree Service

Manages the core domain: trees, chapters, and documents. Documents can be created manually or imported from files/YouTube.

```mermaid
flowchart TD
    USER([User])

    subgraph Frontend
        LIB[Library Page]
        KT[Knowledge Tree Page]
        READER[Document Reader]
    end

    subgraph API["FastAPI — /api/knowledge-trees"]
        RT_TREE[Trees router]
        RT_CH[Chapters router]
        RT_DOC[Documents router]
        LIMIT[Limit checks]
    end

    subgraph App["Application layer"]
        INGEST[Ingest pipeline]
        EXPORT[Tree exporter]
    end

    subgraph DB["PostgreSQL"]
        T[(knowledge_trees)]
        CH[(knowledge_chapters)]
        DOC[(knowledge_documents)]
        CHUNK[(knowledge_content)]
    end

    USER --> LIB
    LIB -->|create / list trees| RT_TREE
    LIB -->|open tree| KT
    KT -->|CRUD chapters| RT_CH
    KT -->|CRUD documents| RT_DOC
    KT -->|import file| INGEST
    KT -->|export ZIP| EXPORT
    KT -->|open doc| READER
    READER -->|read document| RT_DOC

    RT_TREE --> LIMIT --> T
    RT_CH --> CH
    RT_DOC --> DOC
    INGEST --> DOC
    INGEST --> CHUNK
    EXPORT --> T & CH & DOC
```

## Domain hierarchy

```mermaid
flowchart LR
    TREE[KnowledgeTree] -->|1..n| CHAPTER[KnowledgeChapter]
    TREE -->|0..n| DOC_TL[KnowledgeDocument\ntree-level]
    CHAPTER -->|0..n| DOC_CH[KnowledgeDocument\nchapter-level]
    DOC_CH -->|0..n| CHUNK[KnowledgeChunk]
    DOC_TL -->|0..n| CHUNK2[KnowledgeChunk]
```

## Document import pipeline

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as /import
    participant TASK as Task registry
    participant INGEST as Ingest pipeline
    participant DB as PostgreSQL

    User->>FE: upload PDF / EPUB / YouTube URL
    FE->>API: POST /api/knowledge-trees/{id}/chapters/{n}/documents/import
    API->>TASK: create background task → return task_id
    API-->>FE: {task_id}

    loop poll every 2s
        FE->>API: GET /api/tasks/{task_id}
        API-->>FE: {status, progress_pct, progress}
    end

    TASK->>INGEST: run in ThreadPoolExecutor
    INGEST->>INGEST: load (pdf/epub/txt/youtube)
    INGEST->>INGEST: normalize text
    INGEST->>INGEST: SHA-256 dedup check
    INGEST->>INGEST: chapter-aware split → chunks
    INGEST->>DB: INSERT knowledge_documents + knowledge_content
    INGEST->>TASK: mark complete

    FE->>FE: document appears in reader
```

## Data model

```mermaid
erDiagram
    knowledge_trees {
        UUID id PK
        UUID user_id FK
        string title
        string description
        timestamp created_at
    }
    knowledge_chapters {
        UUID id PK
        UUID tree_id FK
        int number
        string title
        timestamp created_at
    }
    knowledge_documents {
        UUID id PK
        UUID tree_id FK
        UUID chapter_id FK "nullable"
        string title
        text content
        text original_content "nullable"
        string source_type "file|youtube"
        string source_url "nullable"
        int page_start
        int page_end
        timestamp created_at
        timestamp updated_at
    }
    knowledge_content {
        UUID id PK
        UUID tree_id FK
        UUID chapter_id FK
        UUID doc_id FK
        int chunk_index
        text text
        int token_count
    }

    knowledge_trees ||--o{ knowledge_chapters : contains
    knowledge_trees ||--o{ knowledge_documents : owns
    knowledge_chapters ||--o{ knowledge_documents : groups
    knowledge_documents ||--o{ knowledge_content : split_into
```
