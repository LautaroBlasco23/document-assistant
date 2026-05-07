# App Overview — User Perspective

This diagram shows the full journey a user takes through the app, from authentication to using knowledge trees.

```mermaid
flowchart TD
    U([User])

    subgraph Browser["Browser (React SPA — port 5173)"]
        AUTH[Login / Register]
        LIB[Library — My Trees]
        TREE[Knowledge Tree View]
        READER[Document Reader]
        CHAT[Chat Panel]
        EXAM[Exam / Quiz]
        SETTINGS[Settings & API Keys]
    end

    subgraph Backend["FastAPI Backend (port 8000)"]
        API[REST API]
    end

    subgraph Storage["Persistence"]
        PG[(PostgreSQL)]
    end

    subgraph LLM["LLM Providers"]
        GROQ[Groq API]
        OLLAMA[Ollama — local]
        OR[OpenRouter]
        HF[HuggingFace]
    end

    U -->|opens app| AUTH
    AUTH -->|JWT token| LIB

    LIB -->|create / open tree| TREE
    TREE -->|import PDF · EPUB · YouTube| READER
    TREE -->|generate flashcards| TREE
    TREE -->|generate questions| EXAM
    TREE -->|export ZIP| U

    READER -->|read & improve text| READER
    READER -->|select text → Ask AI| CHAT

    SETTINGS -->|store encrypted API keys| SETTINGS

    Browser -->|Bearer token + REST calls| API
    API -->|read / write| PG
    API -->|LLM inference| GROQ
    API -.->|optional| OLLAMA
    API -.->|optional| OR
    API -.->|optional| HF
```

## Key user flows

| Flow | Steps |
|------|-------|
| **Import a book** | Library → New Tree → Import PDF/EPUB → background task → chapters + documents appear |
| **Study with AI** | Open document → Improve text → Read improved version → Revert if needed |
| **Chat about content** | Select text in reader → "Ask in chat" → grounded AI answer |
| **Generate flashcards** | Tree view → Generate Flashcards (per chapter) → review cards |
| **Take a quiz** | Tree view → Generate Questions → Start Exam → see score |
| **Export** | Tree view → Export → download ZIP with Markdown + JSON |
