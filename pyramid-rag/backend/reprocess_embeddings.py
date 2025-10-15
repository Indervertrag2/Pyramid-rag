#!/usr/bin/env python3
"""
Script to reprocess all documents and generate missing embeddings.
This is needed when:
1. Embedding model was changed
2. Documents were uploaded without embeddings
3. Database was migrated
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Document, DocumentChunk, DocumentEmbedding
from app.services.document_processor import document_processor
from app.services.embedding_service import EmbeddingService

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize embedding service
embedding_service = EmbeddingService()


async def reprocess_all_documents():
    """Reprocess all documents to generate embeddings."""
    db = SessionLocal()

    try:
        # Get all documents
        docs = db.query(Document).filter(Document.processed == True).all()
        logger.info(f"Found {len(docs)} processed documents")

        # Check embedding statistics
        total_chunks = db.query(func.count(DocumentChunk.id)).scalar()
        total_embeddings = db.query(func.count(DocumentEmbedding.id)).scalar()
        logger.info(f"Current state: {total_embeddings}/{total_chunks} chunks have embeddings")

        if total_embeddings == total_chunks and total_chunks > 0:
            logger.info("All chunks already have embeddings! Nothing to do.")
            return

        # Process each document
        for idx, doc in enumerate(docs, 1):
            logger.info(f"[{idx}/{len(docs)}] Processing document: {doc.original_filename}")

            # Get chunks for this document
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()

            if not chunks:
                logger.warning(f"  No chunks found for document {doc.id}")
                continue

            # Check existing embeddings
            existing_embeddings = db.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_id == doc.id
            ).count()

            if existing_embeddings == len(chunks):
                logger.info(f"  Document already has all embeddings ({existing_embeddings}/{len(chunks)})")
                continue

            logger.info(f"  Found {len(chunks)} chunks, {existing_embeddings} existing embeddings")

            # Delete old embeddings (in case model changed)
            if existing_embeddings > 0:
                logger.info(f"  Deleting {existing_embeddings} old embeddings...")
                db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.document_id == doc.id
                ).delete()
                db.commit()

            # Generate new embeddings
            try:
                logger.info(f"  Generating embeddings for {len(chunks)} chunks...")
                texts = [chunk.content for chunk in chunks]
                embeddings = embedding_service.generate_embeddings(texts)

                if len(embeddings) != len(chunks):
                    logger.error(f"  Embedding count mismatch: got {len(embeddings)}, expected {len(chunks)}")
                    continue

                # Save embeddings to database
                logger.info(f"  Saving {len(embeddings)} embeddings to database...")
                for chunk, embedding_vector in zip(chunks, embeddings):
                    db_embedding = DocumentEmbedding(
                        document_id=doc.id,
                        chunk_id=chunk.id,
                        embedding=embedding_vector,
                        model_name=embedding_service.model_name
                    )
                    db.add(db_embedding)

                db.commit()
                logger.info(f"  ✅ Successfully processed {doc.original_filename}")

            except Exception as e:
                logger.error(f"  ❌ Error processing document {doc.id}: {e}")
                db.rollback()
                continue

        # Final statistics
        total_embeddings_after = db.query(func.count(DocumentEmbedding.id)).scalar()
        logger.info(f"\n{'='*60}")
        logger.info(f"Reprocessing complete!")
        logger.info(f"Before: {total_embeddings}/{total_chunks} chunks with embeddings")
        logger.info(f"After:  {total_embeddings_after}/{total_chunks} chunks with embeddings")
        logger.info(f"Generated: {total_embeddings_after - total_embeddings} new embeddings")
        logger.info(f"{'='*60}\n")

    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting document reprocessing...")
    logger.info(f"Embedding model: {embedding_service.model_name}")
    logger.info(f"Embedding device: {embedding_service.device}")
    logger.info(f"Embedding dimension: {embedding_service.embedding_dim}")
    logger.info("")

    asyncio.run(reprocess_all_documents())
