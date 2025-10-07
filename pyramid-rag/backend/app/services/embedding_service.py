import logging
import os
from typing import List, Optional, Dict, Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
import tiktoken


logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class EmbeddingService:
    """Utility wrapper around sentence-transformers for query/document embeddings."""

    def __init__(self) -> None:
        self.model_name = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2")
        preferred_device = os.getenv("EMBEDDING_DEVICE")
        if preferred_device:
            self.device = preferred_device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.default_chunk_size = _env_int("EMBEDDING_CHUNK_SIZE", 512)
        self.default_chunk_overlap = _env_int("EMBEDDING_CHUNK_OVERLAP", 50)
        self.default_batch_size = _env_int("EMBEDDING_BATCH_SIZE", 16)

        self.model: Optional[SentenceTransformer] = None
        self.tokenizer: Optional[tiktoken.Encoding] = None
        self.embedding_dim: int = 0

        self._initialize_model()

    def _initialize_model(self) -> None:
        """Load the sentence-transformer model and tokenizer."""
        logger.info("Loading embedding model %s on device %s", self.model_name, self.device)

        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            # Resolve embedding dimension lazily if available
            if hasattr(self.model, "get_sentence_embedding_dimension"):
                self.embedding_dim = int(self.model.get_sentence_embedding_dimension())
            else:
                sample = self.model.encode(["probe"], convert_to_numpy=True)
                self.embedding_dim = len(sample[0]) if len(sample) else 0
        except Exception as exc:  # pragma: no cover - hard failure is surfaced to caller
            logger.exception("Failed to load embedding model %s", self.model_name)
            raise

        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def count_tokens(self, text: str) -> int:
        """Estimate token count for a piece of text."""
        if not self.tokenizer:
            raise RuntimeError("Tokenizer not initialised")
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

    def generate_embeddings(self, texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        if not self.model:
            raise RuntimeError("Embedding model not initialised")

        effective_batch_size = batch_size or self.default_batch_size
        vectors: List[np.ndarray] = []

        for start in range(0, len(texts), effective_batch_size):
            batch = texts[start:start + effective_batch_size]
            with torch.no_grad():
                embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
            vectors.extend(embeddings)

        return vectors

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate an embedding vector for a query string."""
        if not self.model:
            raise RuntimeError("Embedding model not initialised")
        with torch.no_grad():
            return self.model.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

    def calculate_similarity(self, query_embedding: np.ndarray, document_embeddings: List[np.ndarray]) -> List[float]:
        """Calculate cosine similarity scores between query and document vectors."""
        if not document_embeddings:
            return []
        doc_matrix = np.vstack(document_embeddings)
        return doc_matrix.dot(query_embedding)

    def rerank_results(self, query: str, results: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Naive rerank helper – returns top_k items by existing score."""
        if not results:
            return []
        return sorted(results, key=lambda item: item.get('score', 0), reverse=True)[:top_k]

    def get_model_info(self) -> Dict[str, Any]:
        """Expose runtime metadata about the embedding backend."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "dimension": self.embedding_dim,
            "max_sequence_length": getattr(self.model, "max_seq_length", 0) if self.model else 0,
            "cuda_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
