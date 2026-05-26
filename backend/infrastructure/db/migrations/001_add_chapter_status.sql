-- Add status column to knowledge_chapters table
ALTER TABLE knowledge_chapters
ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'pending'
CHECK (status IN ('pending', 'read'));
