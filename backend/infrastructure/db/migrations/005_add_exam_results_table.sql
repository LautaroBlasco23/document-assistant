CREATE TABLE IF NOT EXISTS exam_results (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    document_hash  VARCHAR(64)  NOT NULL,
    chapter_index  INTEGER      NOT NULL,
    total_cards    INTEGER      NOT NULL,
    correct_count  INTEGER      NOT NULL,
    passed         BOOLEAN      NOT NULL,
    completed_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_results_doc_chapter
    ON exam_results (document_hash, chapter_index, completed_at DESC);
