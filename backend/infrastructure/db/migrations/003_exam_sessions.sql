CREATE TABLE IF NOT EXISTS exam_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    score FLOAT NOT NULL,
    total_questions INT NOT NULL,
    correct_count INT NOT NULL,
    question_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    results JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_sessions_tree_chapter ON exam_sessions(tree_id, chapter_id);
