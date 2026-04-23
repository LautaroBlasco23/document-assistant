ALTER TABLE knowledge_documents
ADD COLUMN IF NOT EXISTS page_start INT,
ADD COLUMN IF NOT EXISTS page_end INT;
