-- Knowledge Trees
CREATE TABLE IF NOT EXISTS knowledge_trees (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Knowledge Chapters (belongs to a tree)
CREATE TABLE IF NOT EXISTS knowledge_chapters (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id    UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    number     INTEGER NOT NULL,
    title      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tree_id, number)
);

-- Knowledge Documents (raw text content)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id     UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id  UUID REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    is_main     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Knowledge Content (chunked text for LLM processing)
CREATE TABLE IF NOT EXISTS knowledge_content (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id     UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id  UUID NOT NULL REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    doc_id      UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chapters_tree
    ON knowledge_chapters (tree_id, number);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_tree
    ON knowledge_documents (tree_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_chapter
    ON knowledge_documents (chapter_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_content_chapter
    ON knowledge_content (chapter_id);
