#!/usr/bin/env python3
"""
Reprocess all documents with Ollama nomic-embed-text embeddings.
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
from app.services.ollama_embedding_service import OllamaEmbeddingService

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Ollama embedding service
embedding_service = OllamaEmbeddingService()


async def reprocess_all_documents():
    """Reprocess all documents to generate Ollama embeddings."""
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
            logger.info("All chunks already have embeddings!")
            logger.info("Reprocessing with new Ollama model anyway...")

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

            logger.info(f"  Found {len(chunks)} chunks, {existing_embeddings} existing embeddings")

            # Delete old embeddings
            if existing_embeddings > 0:
                logger.info(f"  Deleting {existing_embeddings} old embeddings...")
                db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.document_id == doc.id
                ).delete()
                db.commit()

            # Generate new embeddings with Ollama
            try:
                logger.info(f"  Generating Ollama embeddings for {len(chunks)} chunks...")
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
                        embedding=embedding_vector.tolist(),  # Convert numpy array to list
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
    logger.info("Starting document reprocessing with Ollama embeddings...")
    logger.info(f"Embedding model: {embedding_service.model_name}")
    logger.info(f"Ollama URL: {embedding_service.ollama_base_url}")
    logger.info(f"Embedding dimension: {embedding_service.embedding_dim}")
    logger.info("")

    asyncio.run(reprocess_all_documents())
