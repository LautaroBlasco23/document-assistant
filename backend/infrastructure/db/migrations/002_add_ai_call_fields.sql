-- Add user-scoped AI call tracking fields to background_tasks
-- Applied idempotently on server startup via schema.sql

ALTER TABLE background_tasks ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE background_tasks ADD COLUMN IF NOT EXISTS prompt TEXT NOT NULL DEFAULT '';
ALTER TABLE background_tasks ADD COLUMN IF NOT EXISTS result_excerpt TEXT NOT NULL DEFAULT '';
ALTER TABLE background_tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE background_tasks ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_background_tasks_user_created
    ON background_tasks(user_id, created_at DESC);
