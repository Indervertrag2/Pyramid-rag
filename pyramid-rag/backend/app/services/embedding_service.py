import torch
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import tiktoken
import os


class EmbeddingService:
    def __init__(self):
        self.device = settings.EMBEDDING_DEVICE if torch.cuda.is_available() else 'cpu'
        self.model = None
        self.tokenizer = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the multilingual embedding model."""
        print(f"Lade Embedding-Modell: {settings.EMBEDDING_MODEL}")
        print(f"Verwende Gerät: {self.device}")

        # Load multilingual model that supports German and English
        self.model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device=self.device
        )

        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in text."""
        return len(self.tokenizer.encode(text))

    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separator: str = "\n\n"
    ) -> List[Dict[str, Any]]:
        """Split text into chunks for processing."""
        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # Split by paragraphs first if possible
        if separator in text:
            paragraphs = text.split(separator)
        else:
            # Fallback to sentence splitting
            paragraphs = text.replace('. ', '.\n').split('\n')

        chunks = []
        current_chunk = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)

            # If paragraph is too large, split it further
            if paragraph_tokens > chunk_size:
                # Split by sentences
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    sentence_tokens = self.count_tokens(sentence)

                    if current_tokens + sentence_tokens > chunk_size:
                        if current_chunk:
                            chunk_text = ' '.join(current_chunk)
                            chunks.append({
                                'content': chunk_text,
                                'token_count': self.count_tokens(chunk_text),
                                'chunk_index': len(chunks)
                            })

                            # Keep overlap
                            if chunk_overlap > 0:
                                overlap_sentences = []
                                overlap_tokens = 0
                                for sent in reversed(current_chunk):
                                    sent_tokens = self.count_tokens(sent)
                                    if overlap_tokens + sent_tokens <= chunk_overlap:
                                        overlap_sentences.insert(0, sent)
                                        overlap_tokens += sent_tokens
                                    else:
                                        break
                                current_chunk = overlap_sentences
                                current_tokens = overlap_tokens
                            else:
                                current_chunk = []
                                current_tokens = 0

                    current_chunk.append(sentence)
                    current_tokens += sentence_tokens
            else:
                # Add paragraph to current chunk
                if current_tokens + paragraph_tokens > chunk_size:
                    if current_chunk:
                        chunk_text = separator.join(current_chunk)
                        chunks.append({
                            'content': chunk_text,
                            'token_count': self.count_tokens(chunk_text),
                            'chunk_index': len(chunks)
                        })

                        # Keep overlap
                        if chunk_overlap > 0 and len(current_chunk) > 1:
                            overlap_text = current_chunk[-1]
                            overlap_tokens = self.count_tokens(overlap_text)
                            if overlap_tokens <= chunk_overlap:
                                current_chunk = [overlap_text]
                                current_tokens = overlap_tokens
                            else:
                                current_chunk = []
                                current_tokens = 0
                        else:
                            current_chunk = []
                            current_tokens = 0

                current_chunk.append(paragraph)
                current_tokens += paragraph_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = separator.join(current_chunk) if separator == "\n\n" else ' '.join(current_chunk)
            chunks.append({
                'content': chunk_text,
                'token_count': self.count_tokens(chunk_text),
                'chunk_index': len(chunks)
            })

        return chunks

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """Generate embeddings for a list of texts."""
        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

        if not texts:
            return []

        # Process in batches for memory efficiency
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Generate embeddings
            with torch.no_grad():
                embeddings = self.model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # Normalize for cosine similarity
                    show_progress_bar=False
                )

            all_embeddings.extend(embeddings)

        return all_embeddings

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a search query."""
        with torch.no_grad():
            embedding = self.model.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
        return embedding

    def calculate_similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: List[np.ndarray]
    ) -> List[float]:
        """Calculate cosine similarity between query and documents."""
        if not document_embeddings:
            return []

        # Convert to numpy array for efficient computation
        doc_embeddings_matrix = np.vstack(document_embeddings)

        # Calculate cosine similarity (embeddings are normalized)
        similarities = np.dot(doc_embeddings_matrix, query_embedding)

        return similarities.tolist()

    def rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank search results using cross-encoder if available."""
        if not results:
            return []

        # For now, return top_k results
        # In production, you could use a cross-encoder model for better reranking
        return sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:top_k]

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_name": os.getenv('EMBEDDING_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2'),
            "device": self.device,
            "dimension": int(os.getenv('VECTOR_DIMENSION', '384')),
            "max_sequence_length": self.model.max_seq_length if self.model else 0,
            "cuda_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name() if torch.cuda.is_available() else None
        }