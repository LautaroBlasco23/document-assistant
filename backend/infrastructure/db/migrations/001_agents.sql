CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    prompt TEXT NOT NULL DEFAULT '',
    model VARCHAR(255) NOT NULL,
    temperature FLOAT NOT NULL DEFAULT 0.7,
    top_p FLOAT NOT NULL DEFAULT 1.0,
    max_tokens INT NOT NULL DEFAULT 1024,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_user_default ON agents(user_id, is_default) WHERE is_default = TRUE;
