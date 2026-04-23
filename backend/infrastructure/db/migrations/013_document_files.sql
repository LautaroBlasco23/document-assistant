ALTER TABLE knowledge_documents
ADD COLUMN IF NOT EXISTS source_file_path TEXT,
ADD COLUMN IF NOT EXISTS source_file_name TEXT;

CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    doc_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    source_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flashcards_chapter ON flashcards(chapter_id);
