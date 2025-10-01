-- RAG Pipeline Database Schema
-- Created: 2025-09-26 08:35 UTC

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Document chunks table for RAG
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,
    embedding vector(768), -- For German RoBERTa model
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Create HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

-- Chat files for session-based uploads
CREATE TABLE IF NOT EXISTS chat_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    ingest_enabled BOOLEAN DEFAULT false,
    processing_status VARCHAR(20) DEFAULT 'pending',
    processing_error TEXT,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for session lookups
CREATE INDEX IF NOT EXISTS idx_chat_files_session
ON chat_files(session_id);

-- Index for processing status
CREATE INDEX IF NOT EXISTS idx_chat_files_status
ON chat_files(processing_status);

-- Document processing queue
CREATE TABLE IF NOT EXISTS document_processing_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for queue processing
CREATE INDEX IF NOT EXISTS idx_processing_queue_status
ON document_processing_queue(status, priority DESC, queued_at);

-- Add missing columns to documents table if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'documents'
                   AND column_name = 'chunk_count') THEN
        ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'documents'
                   AND column_name = 'language') THEN
        ALTER TABLE documents ADD COLUMN language VARCHAR(10) DEFAULT 'de';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'documents'
                   AND column_name = 'summary') THEN
        ALTER TABLE documents ADD COLUMN summary TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'documents'
                   AND column_name = 'keywords') THEN
        ALTER TABLE documents ADD COLUMN keywords TEXT[];
    END IF;
END $$;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
DROP TRIGGER IF EXISTS update_document_chunks_updated_at ON document_chunks;
CREATE TRIGGER update_document_chunks_updated_at
BEFORE UPDATE ON document_chunks
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_chat_files_updated_at ON chat_files;
CREATE TRIGGER update_chat_files_updated_at
BEFORE UPDATE ON chat_files
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();