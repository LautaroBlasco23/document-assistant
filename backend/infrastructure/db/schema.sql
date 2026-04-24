-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- SUBSCRIPTION PLANS
-- ============================================

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    max_documents INTEGER NOT NULL DEFAULT 10,
    max_knowledge_trees INTEGER NOT NULL DEFAULT 2,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- USER SUBSCRIPTIONS
-- ============================================

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ============================================
-- KNOWLEDGE TREES (with user ownership)
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_trees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- KNOWLEDGE CHAPTERS
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tree_id, number)
);

-- ============================================
-- KNOWLEDGE DOCUMENTS (with page range)
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id UUID REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    is_main BOOLEAN NOT NULL DEFAULT FALSE,
    source_file_path TEXT,
    source_file_name TEXT,
    page_start INTEGER,
    page_end INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- KNOWLEDGE CONTENT (chunks)
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    doc_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(doc_id, chunk_index)
);

-- ============================================
-- QUESTIONS
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_tree_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL CHECK (question_type IN ('true_false','multiple_choice','matching','checkbox')),
    question_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- FLASHCARDS
-- ============================================

CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES knowledge_trees(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES knowledge_chapters(id) ON DELETE CASCADE,
    doc_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    source_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- TASKS (for background processing)
-- ============================================

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress_pct INTEGER NOT NULL DEFAULT 0,
    progress TEXT NOT NULL DEFAULT '',
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- BACKGROUND TASKS (async job tracking)
-- ============================================

CREATE TABLE IF NOT EXISTS background_tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    doc_hash TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    progress TEXT NOT NULL DEFAULT '',
    progress_pct INTEGER NOT NULL DEFAULT 0,
    chapter INTEGER NOT NULL DEFAULT 0,
    book_title TEXT NOT NULL DEFAULT '',
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON background_tasks(status);

-- ============================================
-- SEED DATA
-- ============================================

INSERT INTO subscription_plans (slug, name, description, max_documents, max_knowledge_trees)
VALUES 
    ('free', 'Free', 'Get started with basic document processing', 10, 2)
ON CONFLICT (slug) DO NOTHING;

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_knowledge_trees_user_id ON knowledge_trees(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chapters_tree ON knowledge_chapters(tree_id, number);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_tree ON knowledge_documents(tree_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_chapter ON knowledge_documents(chapter_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_content_chapter ON knowledge_content(chapter_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_content_doc_chunk ON knowledge_content(doc_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_kt_questions_tree_chapter ON knowledge_tree_questions(tree_id, chapter_id);
CREATE INDEX IF NOT EXISTS idx_kt_questions_tree_chapter_type ON knowledge_tree_questions(tree_id, chapter_id, question_type);
CREATE INDEX IF NOT EXISTS idx_flashcards_chapter ON flashcards(chapter_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
