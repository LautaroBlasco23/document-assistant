ALTER TABLE document_metadata 
ADD COLUMN IF NOT EXISTS file_extension VARCHAR(10) DEFAULT '';
