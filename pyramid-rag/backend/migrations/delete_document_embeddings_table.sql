-- ========================================
-- Migration: Delete document_embeddings Table
-- Date: 2025-10-15
-- Reason: Embeddings now stored directly in document_chunks.embedding
--
-- IMPORTANT: Run this AFTER verifying:
-- 1. All document_chunks have embeddings populated
-- 2. Upload function is fixed (no longer creates DocumentEmbedding records)
-- 3. No code references DocumentEmbedding model
-- ========================================

-- Step 1: Verify all chunks have embeddings (should return row count)
SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    COUNT(*) - COUNT(embedding) as chunks_missing_embeddings
FROM document_chunks;

-- Expected result: chunks_missing_embeddings = 0
-- If > 0, DO NOT run this migration! Fix upload function first.

-- Step 2: Backup check - verify document_embeddings data is redundant
SELECT
    de.id as embedding_id,
    de.chunk_id,
    dc.embedding IS NOT NULL as chunk_has_embedding,
    de.embedding IS NOT NULL as embedding_table_has_data
FROM document_embeddings de
LEFT JOIN document_chunks dc ON de.chunk_id = dc.id
WHERE dc.embedding IS NULL
LIMIT 10;

-- Expected result: No rows (all chunks already have embeddings)
-- If rows exist, data migration is incomplete!

-- Step 3: Check table size before deletion
SELECT
    pg_size_pretty(pg_total_relation_size('document_embeddings')) as table_size,
    COUNT(*) as row_count
FROM document_embeddings;

-- Step 4: DROP the redundant table
-- CAUTION: This is irreversible! Make a backup first if uncertain.

DROP TABLE IF EXISTS document_embeddings CASCADE;

-- Step 5: Verify deletion
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename = 'document_embeddings';

-- Expected result: No rows (table is deleted)

-- Step 6: Verify related models/tables still intact
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('documents', 'document_chunks', 'chat_file_embeddings')
ORDER BY tablename;

-- Expected result: All three tables exist and have data

-- ========================================
-- Post-Migration Checklist:
-- ========================================
-- [ ] Verify all document_chunks have embeddings
-- [ ] Test document upload (new documents should be searchable)
-- [ ] Test vector search (should return results)
-- [ ] Check backend logs for errors
-- [ ] Update models.py (remove DocumentEmbedding class if not used elsewhere)
-- [ ] Restart backend service
-- ========================================
