CREATE TABLE IF NOT EXISTS document_content (
    file_hash VARCHAR PRIMARY KEY,
    content TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);