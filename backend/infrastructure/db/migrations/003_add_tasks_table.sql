CREATE TABLE IF NOT EXISTS background_tasks (
    task_id       VARCHAR(36)  PRIMARY KEY,
    task_type     VARCHAR(20)  NOT NULL,  -- ingest | summarize | flashcards
    doc_hash      VARCHAR(64)  NOT NULL DEFAULT '',
    filename      VARCHAR(255) NOT NULL DEFAULT '',
    status        VARCHAR(20)  NOT NULL,  -- pending | running | completed | failed
    progress      TEXT         NOT NULL DEFAULT '',
    progress_pct  INTEGER      NOT NULL DEFAULT 0,
    result        JSONB       ,
    error         TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_background_tasks_status
    ON background_tasks (status)
    WHERE status IN ('pending', 'running');
