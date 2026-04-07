CREATE TABLE IF NOT EXISTS summaries (
    document_hash  VARCHAR(64)  NOT NULL,
    chapter_index  INTEGER      NOT NULL,
    content        TEXT         NOT NULL,
    description    TEXT         NOT NULL DEFAULT '',
    bullets        TEXT         NOT NULL DEFAULT '[]',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_hash, chapter_index)
);

CREATE TABLE IF NOT EXISTS flashcards (
    id               UUID         PRIMARY KEY,
    document_hash    VARCHAR(64)  NOT NULL,
    chapter_index    INTEGER      NOT NULL,
    front            TEXT         NOT NULL,
    back             TEXT         NOT NULL,
    source_page      INTEGER,
    source_chunk_id  VARCHAR(64)  NOT NULL DEFAULT '',
    source_text      TEXT         NOT NULL DEFAULT '',
    status           VARCHAR(10)  NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flashcards_doc_chapter
    ON flashcards (document_hash, chapter_index);

CREATE TABLE IF NOT EXISTS document_metadata (
    document_hash  VARCHAR(64)  PRIMARY KEY,
    description    TEXT         NOT NULL DEFAULT '',
    document_type  VARCHAR(50)  NOT NULL DEFAULT '',
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

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
