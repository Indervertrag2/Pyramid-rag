-- ========================================
-- Migration: Upgrade to BGE-M3 (1024 dimensions)
-- Date: 2025-10-15
-- Purpose: Migrate from old embedding model (768 dim) to BGE-M3 (1024 dim)
--
-- IMPORTANT: This requires re-embedding ALL documents!
-- ========================================

-- Step 1: Check current state
SELECT
    'document_chunks' as table_name,
    COUNT(*) as total_rows,
    COUNT(embedding) as rows_with_embeddings,
    COUNT(*) - COUNT(embedding) as rows_without_embeddings
FROM document_chunks

UNION ALL

SELECT
    'document_embeddings' as table_name,
    COUNT(*) as total_rows,
    COUNT(embedding) as rows_with_embeddings,
    COUNT(*) - COUNT(embedding) as rows_without_embeddings
FROM document_embeddings

UNION ALL

SELECT
    'chat_file_embeddings' as table_name,
    COUNT(*) as total_rows,
    COUNT(embedding) as rows_with_embeddings,
    COUNT(*) - COUNT(embedding) as rows_without_embeddings
FROM chat_file_embeddings;

-- Step 2: BACKUP existing embeddings (CRITICAL!)
-- Create backup table with old 768-dimensional embeddings
CREATE TABLE document_chunks_backup_768dim AS
SELECT * FROM document_chunks WHERE embedding IS NOT NULL;

CREATE TABLE document_embeddings_backup_768dim AS
SELECT * FROM document_embeddings WHERE embedding IS NOT NULL;

CREATE TABLE chat_file_embeddings_backup_768dim AS
SELECT * FROM chat_file_embeddings WHERE embedding IS NOT NULL;

SELECT
    'Backup created' as status,
    (SELECT COUNT(*) FROM document_chunks_backup_768dim) as chunks_backed_up,
    (SELECT COUNT(*) FROM document_embeddings_backup_768dim) as embeddings_backed_up,
    (SELECT COUNT(*) FROM chat_file_embeddings_backup_768dim) as chat_embeddings_backed_up;

-- Step 3: Clear existing embeddings
-- WARNING: This deletes all 768-dimensional embeddings!
-- Make sure backup was successful before running!

UPDATE document_chunks SET embedding = NULL;
UPDATE document_embeddings SET embedding = NULL;
UPDATE chat_file_embeddings SET embedding = NULL;

SELECT 'Old embeddings cleared' as status;

-- Step 4: Alter vector column dimensions
-- Change from vector(768) to vector(1024)

ALTER TABLE document_chunks
    ALTER COLUMN embedding TYPE vector(1024);

ALTER TABLE document_embeddings
    ALTER COLUMN embedding TYPE vector(1024);

ALTER TABLE chat_file_embeddings
    ALTER COLUMN embedding TYPE vector(1024);

SELECT 'Vector columns upgraded to 1024 dimensions' as status;

-- Step 5: Drop old HNSW indexes (they're for 768 dimensions)
DROP INDEX IF EXISTS document_chunks_embedding_idx;
DROP INDEX IF EXISTS document_embeddings_embedding_idx;
DROP INDEX IF EXISTS chat_file_embeddings_embedding_idx;

SELECT 'Old HNSW indexes dropped' as status;

-- Step 6: Create NEW HNSW indexes for 1024 dimensions
-- Optimized parameters for BGE-M3

CREATE INDEX document_chunks_embedding_idx_bge_m3
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX document_embeddings_embedding_idx_bge_m3
    ON document_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX chat_file_embeddings_embedding_idx_bge_m3
    ON chat_file_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

SELECT 'New HNSW indexes created for BGE-M3' as status;

-- Step 7: Verify migration
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE '%embedding%bge%'
ORDER BY tablename;

-- ========================================
-- POST-MIGRATION: Re-embed all documents
-- ========================================

-- After running this migration, you MUST re-embed all documents:
--
-- 1. Restart backend with new BGE-M3 config:
--    docker-compose restart pyramid-backend
--
-- 2. Run re-embedding script:
--    docker exec -it pyramid-backend python reprocess_embeddings.py
--
-- 3. Verify embeddings were generated:
--    SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;
--
-- 4. Test search functionality:
--    curl -X POST http://localhost:18000/api/v1/search \
--      -H "Authorization: Bearer YOUR_TOKEN" \
--      -d '{"query": "test", "mode": "HYBRID"}'
--
-- ========================================

-- Step 8: Cleanup (OPTIONAL - only after successful migration)
-- Drop backup tables after you've verified everything works

-- DROP TABLE IF EXISTS document_chunks_backup_768dim;
-- DROP TABLE IF EXISTS document_embeddings_backup_768dim;
-- DROP TABLE IF EXISTS chat_file_embeddings_backup_768dim;

-- ========================================
-- Rollback Plan (if migration fails)
-- ========================================

-- If migration fails, restore from backup:
--
-- 1. Alter columns back to 768 dimensions:
--    ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768);
--    ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE vector(768);
--    ALTER TABLE chat_file_embeddings ALTER COLUMN embedding TYPE vector(768);
--
-- 2. Restore embeddings from backup:
--    UPDATE document_chunks dc
--    SET embedding = b.embedding
--    FROM document_chunks_backup_768dim b
--    WHERE dc.id = b.id;
--
--    UPDATE document_embeddings de
--    SET embedding = b.embedding
--    FROM document_embeddings_backup_768dim b
--    WHERE de.id = b.id;
--
--    UPDATE chat_file_embeddings cfe
--    SET embedding = b.embedding
--    FROM chat_file_embeddings_backup_768dim b
--    WHERE cfe.id = b.id;
--
-- 3. Recreate old indexes:
--    CREATE INDEX document_chunks_embedding_idx
--        ON document_chunks USING hnsw (embedding vector_cosine_ops)
--        WITH (m = 16, ef_construction = 64);
--
-- 4. Verify restoration:
--    SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;
--
-- ========================================
