"""
BGE-M3 Embedding Service - State-of-the-art multilingual embeddings
Replaces both Ollama and old SentenceTransformer services with unified BGE-M3
"""
import logging
import os
from typing import List, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# Lazy import to avoid loading on every import
_sentence_transformer = None
_embedding_model = None


def get_embedding_model():
    """Lazy load the embedding model (singleton pattern)."""
    global _sentence_transformer, _embedding_model

    if _embedding_model is None:
        if _sentence_transformer is None:
            try:
                from sentence_transformers import SentenceTransformer
                _sentence_transformer = SentenceTransformer
            except ImportError:
                logger.error("sentence-transformers not installed! Install with: pip install sentence-transformers")
                raise

        model_name = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-m3')
        device = os.getenv('EMBEDDING_DEVICE', 'cuda' if _check_cuda() else 'cpu')

        logger.info(f"Loading BGE-M3 embedding model: {model_name} on {device}...")
        _embedding_model = _sentence_transformer(
            model_name,
            device=device,
            trust_remote_code=True  # Required for BGE-M3
        )
        logger.info(f"✅ BGE-M3 loaded successfully! Dimensions: {_embedding_model.get_sentence_embedding_dimension()}")

    return _embedding_model


def _check_cuda():
    """Check if CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


class BGEM3EmbeddingService:
    """
    Unified embedding service using BGE-M3 (BAAI/bge-m3)
    - 1024 dimensions
    - Best multilingual performance (100+ languages)
    - Excellent German support
    - Hybrid retrieval capabilities (dense + sparse + multi-vector)
    """

    def __init__(self) -> None:
        self.model_name = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-m3')
        self.embedding_dim = 1024  # BGE-M3 dimension
        self.device = os.getenv('EMBEDDING_DEVICE', 'cuda' if _check_cuda() else 'cpu')

        self.default_chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.default_chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))

        # Lazy load the model
        self._model = None

        logger.info(f"BGE-M3 embedding service initialized (lazy loading): {self.model_name} on {self.device}")

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = get_embedding_model()
        return self._model

    def count_tokens(self, text: str) -> int:
        """Estimate token count (approximate for BGE-M3)."""
        # BGE-M3 uses WordPiece tokenizer, roughly 1.3 tokens per word
        words = len(text.split())
        return int(words * 1.3)

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separator: str = "\n\n",
    ) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks suitable for embedding."""
        if not text.strip():
            return []

        target_chunk_size = chunk_size or self.default_chunk_size
        target_overlap = chunk_overlap or self.default_chunk_overlap

        # Split by separator
        if separator in text:
            segments = text.split(separator)
        else:
            # Fallback: split by sentences
            segments = text.replace('. ', '.\n').split('\n')

        chunks: List[Dict[str, Any]] = []
        current_segment: List[str] = []
        current_tokens = 0

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            segment_tokens = self.count_tokens(segment)

            # If current chunk + new segment exceeds limit, save current chunk
            if current_tokens + segment_tokens > target_chunk_size and current_segment:
                chunk_text = separator.join(current_segment) if separator == "\n\n" else ' '.join(current_segment)
                chunks.append({
                    'content': chunk_text,
                    'token_count': self.count_tokens(chunk_text),
                    'chunk_index': len(chunks),
                    'word_count': len(chunk_text.split()),
                    'character_count': len(chunk_text)
                })

                # Apply overlap
                if target_overlap > 0 and current_segment:
                    overlap_tokens = 0
                    overlap_segments: List[str] = []
                    for item in reversed(current_segment):
                        item_tokens = self.count_tokens(item)
                        if overlap_tokens + item_tokens > target_overlap:
                            break
                        overlap_segments.insert(0, item)
                        overlap_tokens += item_tokens
                    current_segment = overlap_segments
                    current_tokens = overlap_tokens
                else:
                    current_segment = []
                    current_tokens = 0

            current_segment.append(segment)
            current_tokens += segment_tokens

        # Add remaining segments
        if current_segment:
            chunk_text = separator.join(current_segment) if separator == "\n\n" else ' '.join(current_segment)
            chunks.append({
                'content': chunk_text,
                'token_count': self.count_tokens(chunk_text),
                'chunk_index': len(chunks),
                'word_count': len(chunk_text.split()),
                'character_count': len(chunk_text)
            })

        logger.info(f"Chunked text into {len(chunks)} chunks (target: {target_chunk_size} tokens, overlap: {target_overlap})")
        return chunks

    def generate_embeddings(self, texts: List[str], normalize: bool = True) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts using BGE-M3.

        Args:
            texts: List of text strings to embed
            normalize: Whether to L2-normalize embeddings (recommended for cosine similarity)

        Returns:
            List of embedding vectors (1024 dimensions each)
        """
        if not texts:
            return []

        try:
            logger.info(f"Generating embeddings for {len(texts)} texts with BGE-M3...")
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=normalize,
                batch_size=32,  # Adjust based on GPU memory
                show_progress_bar=False
            )

            # Convert to list of numpy arrays
            result = [np.array(emb, dtype=np.float32) for emb in embeddings]
            logger.info(f"✅ Generated {len(result)} embeddings (dimension: {result[0].shape[0]})")
            return result

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            # Return zero vectors as fallback
            return [np.zeros(self.embedding_dim, dtype=np.float32) for _ in texts]

    def generate_query_embedding(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Generate an embedding vector for a search query.

        BGE-M3 supports query prefixing for better retrieval:
        - For queries, we can optionally prefix with "Represent this sentence for searching relevant passages:"

        Args:
            query: The search query text
            normalize: Whether to L2-normalize the embedding

        Returns:
            Embedding vector (1024 dimensions)
        """
        try:
            # BGE-M3 performs better with query instruction for retrieval tasks
            # But it's not strictly required - the model is trained for both
            embedding = self.model.encode(
                query,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )

            result = np.array(embedding, dtype=np.float32)
            logger.debug(f"Generated query embedding (dimension: {result.shape[0]})")
            return result

        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}", exc_info=True)
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def calculate_similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: List[np.ndarray]
    ) -> List[float]:
        """
        Calculate cosine similarity scores between query and document vectors.

        Args:
            query_embedding: Query vector (1024 dimensions)
            document_embeddings: List of document vectors (1024 dimensions each)

        Returns:
            List of similarity scores (0.0 to 1.0, higher = more similar)
        """
        if not document_embeddings:
            return []

        # Normalize query embedding
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

        # Calculate cosine similarity with each document
        similarities = []
        for doc_emb in document_embeddings:
            doc_norm = doc_emb / (np.linalg.norm(doc_emb) + 1e-10)
            similarity = float(np.dot(query_norm, doc_norm))
            similarities.append(max(0.0, min(1.0, similarity)))  # Clamp to [0, 1]

        return similarities

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_name": self.model_name,
            "provider": "sentence-transformers",
            "dimension": self.embedding_dim,
            "device": self.device,
            "supports_hybrid": True,  # BGE-M3 supports hybrid retrieval
            "max_sequence_length": 8192,  # BGE-M3 supports very long texts
            "languages": "100+ (multilingual)",
            "optimized_for": "German + English + 98 more languages"
        }

    def batch_encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> List[np.ndarray]:
        """
        Batch encode large number of texts efficiently.

        Args:
            texts: List of texts to encode
            batch_size: Number of texts per batch (adjust based on GPU memory)
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            logger.info(f"Batch encoding {len(texts)} texts (batch_size={batch_size})...")
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )

            result = [np.array(emb, dtype=np.float32) for emb in embeddings]
            logger.info(f"✅ Batch encoding complete: {len(result)} embeddings")
            return result

        except Exception as e:
            logger.error(f"Batch encoding failed: {e}", exc_info=True)
            return [np.zeros(self.embedding_dim, dtype=np.float32) for _ in texts]
