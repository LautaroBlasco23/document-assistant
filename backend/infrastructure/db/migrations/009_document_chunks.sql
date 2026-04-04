CREATE TABLE IF NOT EXISTS document_chunks (
    file_hash      VARCHAR(64)  NOT NULL,
    chapter_index  INTEGER      NOT NULL,
    chunk_index    INTEGER      NOT NULL,
    text           TEXT         NOT NULL,
    page_number    INTEGER,
    token_count    INTEGER      NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (file_hash, chapter_index, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_file
    ON document_chunks (file_hash);

CREATE INDEX IF NOT EXISTS idx_document_chunks_chapter
    ON document_chunks (file_hash, chapter_index);
