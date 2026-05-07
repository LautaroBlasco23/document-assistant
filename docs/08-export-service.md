# Export Service

Generates a ZIP archive of an entire knowledge tree — chapters as folders, documents as Markdown files, flashcards and questions as structured JSON.

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as GET /export
    participant EXPORTER as tree_exporter\n(application/export)
    participant DB as PostgreSQL

    User->>FE: click "Export Tree"
    FE->>API: GET /api/knowledge-trees/{id}/export\n(Authorization: Bearer token)
    API->>DB: fetch tree + chapters + documents\n+ flashcards + questions
    DB-->>API: full tree data
    API->>EXPORTER: build_zip(tree_data)

    loop for each chapter
        EXPORTER->>EXPORTER: create chapter/ folder
        loop for each document
            EXPORTER->>EXPORTER: write document.md\n(title + content as Markdown)
        end
        EXPORTER->>EXPORTER: write flashcards.json
        EXPORTER->>EXPORTER: write questions.json
    end

    EXPORTER->>EXPORTER: write tree_meta.json\n(title, description, created_at)
    EXPORTER-->>API: ZIP bytes (in-memory)
    API-->>FE: response (application/zip)\nContent-Disposition: attachment
    FE->>FE: browser triggers download
```

## ZIP archive structure

```
{tree_title}/
├── tree_meta.json              # title, description, created_at, chapter count
├── chapter_01_{title}/
│   ├── 01_{doc_title}.md       # document content as Markdown
│   ├── 02_{doc_title}.md
│   ├── flashcards.json         # [{front, back, source_text}]
│   └── questions.json          # [{question_type, question_data}]
├── chapter_02_{title}/
│   └── ...
└── (tree-level documents)
    └── {doc_title}.md
```

## Export data included per document

| Field | Included | Notes |
|-------|----------|-------|
| Title | yes | used as filename |
| Content | yes | current version (improved if applicable) |
| Original content | no | not exported |
| Source file name | yes | in document front-matter |
| Source type | yes | `file` or `youtube` |
| Source URL | yes | YouTube URL when applicable |
| Page range | yes | `page_start` / `page_end` |
