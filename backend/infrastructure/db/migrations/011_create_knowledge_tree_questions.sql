CREATE TABLE IF NOT EXISTS knowledge_tree_questions (
    id            UUID PRIMARY KEY,
    tree_id       UUID NOT NULL,
    chapter_id    UUID NOT NULL,
    question_type TEXT NOT NULL CHECK (question_type IN ('true_false','multiple_choice','matching','checkbox')),
    question_data JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kt_questions_tree_chapter
    ON knowledge_tree_questions (tree_id, chapter_id);

CREATE INDEX IF NOT EXISTS idx_kt_questions_tree_chapter_type
    ON knowledge_tree_questions (tree_id, chapter_id, question_type);
