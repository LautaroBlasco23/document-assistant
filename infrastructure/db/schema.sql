CREATE TABLE IF NOT EXISTS summaries (
    document_hash  VARCHAR(64)  NOT NULL,
    chapter_index  INTEGER      NOT NULL,
    content        TEXT         NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_hash, chapter_index)
);

CREATE TABLE IF NOT EXISTS qa_pairs (
    id             UUID         PRIMARY KEY,
    document_hash  VARCHAR(64)  NOT NULL,
    chapter_index  INTEGER      NOT NULL,
    question       TEXT         NOT NULL,
    answer         TEXT         NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_pairs_doc_chapter
    ON qa_pairs (document_hash, chapter_index);

CREATE TABLE IF NOT EXISTS flashcards (
    id             UUID         PRIMARY KEY,
    document_hash  VARCHAR(64)  NOT NULL,
    chapter_index  INTEGER      NOT NULL,
    front          TEXT         NOT NULL,
    back           TEXT         NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flashcards_doc_chapter
    ON flashcards (document_hash, chapter_index);
