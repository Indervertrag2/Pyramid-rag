"""Ollama-based embedding service using nomic-embed-text model."""
import logging
import os
from typing import List, Optional, Dict, Any
import requests
import numpy as np
import tiktoken

logger = logging.getLogger(__name__)


class OllamaEmbeddingService:
    """Embedding service using Ollama's nomic-embed-text model."""

    def __init__(self) -> None:
        self.model_name = "nomic-embed-text:v1.5"
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.embedding_dim = 768  # nomic-embed-text dimension

        self.default_chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.default_chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))

        self.tokenizer: Optional[tiktoken.Encoding] = None
        self._initialize_tokenizer()

        logger.info(f"Ollama embedding service initialized: {self.model_name} @ {self.ollama_base_url}")

    def _initialize_tokenizer(self) -> None:
        """Load tokenizer for text chunking."""
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def count_tokens(self, text: str) -> int:
        """Estimate token count for a piece of text."""
        if not self.tokenizer:
            raise RuntimeError("Tokenizer not initialized")
        return len(self.tokenizer.encode(text))

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

        if separator in text:
            segments = text.split(separator)
        else:
            segments = text.replace('. ', '.\n').split('\n')

        chunks: List[Dict[str, Any]] = []
        current_segment: List[str] = []
        current_tokens = 0

        for segment in segments:
            segment_tokens = self.count_tokens(segment) if segment else 0

            if current_tokens + segment_tokens > target_chunk_size and current_segment:
                chunk_text = separator.join(current_segment) if separator == "\n\n" else ' '.join(current_segment)
                chunks.append({
                    'content': chunk_text,
                    'token_count': self.count_tokens(chunk_text),
                    'chunk_index': len(chunks)
                })

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

        if current_segment:
            chunk_text = separator.join(current_segment) if separator == "\n\n" else ' '.join(current_segment)
            chunks.append({
                'content': chunk_text,
                'token_count': self.count_tokens(chunk_text),
                'chunk_index': len(chunks)
            })

        return chunks

    def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts using Ollama."""
        if not texts:
            return []

        embeddings = []
        for text in texts:
            try:
                response = requests.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": text
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                embedding = np.array(data["embedding"], dtype=np.float32)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                # Return zero vector as fallback
                embeddings.append(np.zeros(self.embedding_dim, dtype=np.float32))

        return embeddings

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate an embedding vector for a query string."""
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": query
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return np.array(data["embedding"], dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def calculate_similarity(self, query_embedding: np.ndarray, document_embeddings: List[np.ndarray]) -> List[float]:
        """Calculate cosine similarity scores between query and document vectors."""
        if not document_embeddings:
            return []

        # Normalize query embedding
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

        # Normalize document embeddings and calculate dot product
        similarities = []
        for doc_emb in document_embeddings:
            doc_norm = doc_emb / (np.linalg.norm(doc_emb) + 1e-10)
            similarity = float(np.dot(query_norm, doc_norm))
            similarities.append(similarity)

        return similarities

    def get_model_info(self) -> Dict[str, Any]:
        """Expose runtime metadata about the embedding backend."""
        return {
            "model_name": self.model_name,
            "provider": "ollama",
            "dimension": self.embedding_dim,
            "ollama_url": self.ollama_base_url,
        }
