"""
Vector Embeddings Service
Generates embeddings for documents using sentence-transformers
"""

import os
import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID

from app.models import Document, DocumentChunk, DocumentEmbedding
from app.database import get_db

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Service for generating and managing document embeddings"""

    def __init__(self):
        # Use multilingual model for German/English support
        # This model produces 384-dimensional embeddings
        self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        self.embedding_dim = 384
        self.model: Optional[SentenceTransformer] = None
        self._load_model()

    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not self.model:
            self._load_model()

        if not text.strip():
            return [0.0] * self.embedding_dim

        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_tensor=False, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding for text: {e}")
            return [0.0] * self.embedding_dim

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts (more efficient)"""
        if not self.model:
            self._load_model()

        if not texts:
            return []

        try:
            # Clean empty texts
            cleaned_texts = [text.strip() if text.strip() else " " for text in texts]

            # Generate embeddings in batch
            embeddings = self.model.encode(cleaned_texts, convert_to_tensor=False, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [[0.0] * self.embedding_dim] * len(texts)

    async def process_document_embeddings(self, document_id: str, db: Session) -> bool:
        """Generate embeddings for all chunks of a document"""
        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return False

            # Get all chunks for this document
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return True

            logger.info(f"Processing embeddings for document {document_id} with {len(chunks)} chunks")

            # Extract texts from chunks
            chunk_texts = [chunk.content for chunk in chunks]

            # Generate embeddings in batch
            embeddings = self.generate_embeddings_batch(chunk_texts)

            # Save embeddings to database
            for chunk, embedding_vector in zip(chunks, embeddings):
                # Check if embedding already exists
                existing_embedding = db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.chunk_id == chunk.id,
                    DocumentEmbedding.model_name == self.model_name
                ).first()

                if existing_embedding:
                    # Update existing embedding
                    existing_embedding.embedding = embedding_vector
                else:
                    # Create new embedding
                    doc_embedding = DocumentEmbedding(
                        document_id=document.id,
                        chunk_id=chunk.id,
                        embedding=embedding_vector,
                        model_name=self.model_name
                    )
                    db.add(doc_embedding)

            db.commit()
            logger.info(f"Successfully generated embeddings for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing embeddings for document {document_id}: {e}")
            db.rollback()
            return False

    def find_similar_chunks(self, query_text: str, db: Session, limit: int = 10,
                          department_filter: Optional[str] = None) -> List[dict]:
        """Find similar chunks using vector similarity search"""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embedding(query_text)

            # For now, use simple cosine similarity in Python
            # In production, this should use pgvector's similarity search

            # Get all embeddings (with department filter if specified)
            query = db.query(DocumentEmbedding, DocumentChunk, Document).join(
                DocumentChunk, DocumentEmbedding.chunk_id == DocumentChunk.id
            ).join(
                Document, DocumentEmbedding.document_id == Document.id
            ).filter(
                DocumentEmbedding.model_name == self.model_name
            )

            if department_filter:
                from app.models import Department
                query = query.filter(Document.department == Department(department_filter))

            embeddings_data = query.all()

            # Calculate similarities
            similarities = []
            for embedding_obj, chunk, document in embeddings_data:
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, embedding_obj.embedding)
                similarities.append({
                    'chunk_id': str(chunk.id),
                    'document_id': str(document.id),
                    'document_title': document.title,
                    'chunk_content': chunk.content,
                    'similarity': similarity,
                    'chunk_index': chunk.chunk_index
                })

            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)

            return similarities[:limit]

        except Exception as e:
            logger.error(f"Error finding similar chunks: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def get_model_info(self) -> dict:
        """Get information about the current embedding model"""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "is_loaded": self.model is not None
        }

# Global instance
embeddings_service = EmbeddingsService()