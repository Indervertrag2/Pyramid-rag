import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, cast
from sqlalchemy.dialects.postgresql import JSONB

from app.models import Document, DocumentChunk, DocumentEmbedding, Department
from app.embeddings_service import embeddings_service

logger = logging.getLogger(__name__)

class VectorStore:
    """Vector store for semantic document search"""

    def __init__(self):
        self.embeddings_service = embeddings_service

    async def semantic_search(
        self,
        query: str,
        db: Session,
        limit: int = 10,
        similarity_threshold: float = 0.1,
        user_department: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector embeddings
        """
        try:
            logger.info(f"Performing semantic search for query: '{query[:100]}...'")
            query_embedding = embeddings_service.generate_embedding(query)

            # Build base query
            base_query = db.query(
                DocumentEmbedding,
                DocumentChunk,
                Document
            ).join(
                DocumentChunk, DocumentEmbedding.chunk_id == DocumentChunk.id
            ).join(
                Document, DocumentEmbedding.document_id == Document.id
            ).filter(
                DocumentEmbedding.model_name == embeddings_service.model_name
            )

            # Apply department-based access control
            if user_department:
                try:
                    dept_enum = Department(user_department)
                    visibility_json = cast(Document.meta_data, JSONB)["visibility"].astext
                    allowed_departments_json = cast(Document.meta_data, JSONB)["allowed_departments"]
                    base_query = base_query.filter(
                        or_(
                            Document.department == dept_enum,
                            visibility_json == "all",
                            and_(
                                allowed_departments_json.isnot(None),
                                allowed_departments_json.contains([dept_enum.value]),
                            ),
                            and_(
                                allowed_departments_json.isnot(None),
                                allowed_departments_json.contains([dept_enum.name]),
                            ),
                            and_(
                                allowed_departments_json.isnot(None),
                                allowed_departments_json.contains(["ALL"]),
                            ),
                        )
                    )
                except ValueError:
                    logger.warning(f"Invalid department: {user_department}")

            # Get all matching embeddings
            embeddings_data = base_query.all()

            if not embeddings_data:
                logger.info("No embeddings found matching the criteria")
                return []

            # Calculate similarities
            results = []
            for embedding_obj, chunk, document in embeddings_data:
                try:
                    similarity = self._cosine_similarity(query_embedding, embedding_obj.embedding)

                    if similarity >= similarity_threshold:
                        visibility = None
                        if document.meta_data:
                            visibility = document.meta_data.get("visibility")

                        meta = document.meta_data or {}
                        raw_allowed = meta.get('allowed_departments')
                        if isinstance(raw_allowed, list):
                            allowed_departments = [str(dep) for dep in raw_allowed if dep]
                        elif raw_allowed:
                            allowed_departments = [str(raw_allowed)]
                        else:
                            allowed_departments = []

                        results.append({
                            'chunk_id': str(chunk.id),
                            'document_id': str(document.id),
                            'document_title': document.title or document.filename,
                            'document_filename': document.filename,
                            'chunk_content': chunk.content,
                            'chunk_index': chunk.chunk_index,
                            'similarity_score': round(similarity, 4),
                            'department': document.department.value if document.department else None,
                            'visibility': visibility,
                            'file_type': document.file_type.value if document.file_type else None,
                            'created_at': document.created_at.isoformat() if document.created_at else None,
                            'meta_data': chunk.meta_data or {},
                            'allowed_departments': allowed_departments,
                            'scope': 'GLOBAL',
                            'source': 'knowledge_base',
                        })
                except Exception as e:
                    logger.error(f"Error calculating similarity for chunk {chunk.id}: {e}")
                    continue

            # Sort by similarity and limit results
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:limit]

            logger.info(f"Found {len(results)} semantic search results")
            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def keyword_search(
        self,
        query: str,
        db: Session,
        limit: int = 10,
        user_department: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search in document content
        """
        try:
            logger.info(f"Performing keyword search for query: '{query[:100]}...'")

            search_terms = query.lower().split()
            base_query = db.query(
                DocumentChunk,
                Document
            ).join(
                Document, DocumentChunk.document_id == Document.id
            )

            # Apply department-based access control
            if user_department:
                try:
                    dept_enum = Department(user_department)
                    visibility_json = cast(Document.meta_data, JSONB)["visibility"].astext
                    allowed_departments_json = cast(Document.meta_data, JSONB)["allowed_departments"]
                    base_query = base_query.filter(
                        or_(
                            Document.department == dept_enum,
                            visibility_json == "all",
                            and_(
                                allowed_departments_json.isnot(None),
                                allowed_departments_json.contains([dept_enum.value]),
                            ),
                            and_(
                                allowed_departments_json.isnot(None),
                                allowed_departments_json.contains([dept_enum.name]),
                            ),
                            and_(
                                allowed_departments_json.isnot(None),
                                allowed_departments_json.contains(["ALL"]),
                            ),
                        )
                    )
                except ValueError:
                    logger.warning(f"Invalid department: {user_department}")

            # Apply keyword filters
            keyword_conditions = []
            for term in search_terms:
                keyword_conditions.append(DocumentChunk.content.ilike(f'%{term}%'))

            base_query = base_query.filter(or_(*keyword_conditions))
            search_results = base_query.limit(limit * 2).all()

            # Rank results by keyword matches
            results = []
            for chunk, document in search_results:
                content_lower = chunk.content.lower()
                match_count = sum(1 for term in search_terms if term in content_lower)
                match_score = match_count / len(search_terms)

                visibility = None
                if document.meta_data:
                    visibility = document.meta_data.get("visibility")

                meta = document.meta_data or {}
                raw_allowed = meta.get('allowed_departments')
                if isinstance(raw_allowed, list):
                    allowed_departments = [str(dep) for dep in raw_allowed if dep]
                elif raw_allowed:
                    allowed_departments = [str(raw_allowed)]
                else:
                    allowed_departments = []

                results.append({
                    'document_id': str(document.id),
                    'document_title': document.title or document.filename,
                    'chunk_content': chunk.content,
                    'chunk_id': str(chunk.id),
                    'keyword_score': round(match_score, 4),
                    'department': document.department.value if document.department else None,
                    'visibility': meta.get('visibility') if meta else None,
                    'file_type': document.file_type.value if document.file_type else None,
                    'created_at': document.created_at.isoformat() if document.created_at else None,
                    'allowed_departments': allowed_departments,
                    'scope': 'GLOBAL',
                    'source': 'knowledge_base',
                })

            results.sort(key=lambda x: x['keyword_score'], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        db: Session,
        limit: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        user_department: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search
        """
        try:
            logger.info(f"Performing hybrid search for query: '{query[:100]}...'")

            # Perform both searches
            semantic_results = await self.semantic_search(
                query, db, limit * 2, user_department=user_department, filters=filters
            )
            keyword_results = await self.keyword_search(
                query, db, limit * 2, user_department=user_department, filters=filters
            )

            # Combine and score results
            combined_results = {}

            # Add semantic results
            for result in semantic_results:
                chunk_id = result['chunk_id']
                combined_results[chunk_id] = result.copy()
                combined_results[chunk_id]['semantic_score'] = result['similarity_score']
                combined_results[chunk_id]['keyword_score'] = 0.0

            # Add/merge keyword results
            for result in keyword_results:
                chunk_id = result['chunk_id']
                if chunk_id in combined_results:
                    combined_results[chunk_id]['keyword_score'] = result['keyword_score']
                else:
                    combined_results[chunk_id] = result.copy()
                    combined_results[chunk_id]['semantic_score'] = 0.0
                    combined_results[chunk_id]['keyword_score'] = result['keyword_score']

            # Calculate hybrid scores
            final_results = []
            for chunk_id, result in combined_results.items():
                semantic_score = result.get('semantic_score', 0.0)
                keyword_score = result.get('keyword_score', 0.0)

                hybrid_score = (semantic_score * semantic_weight) + (keyword_score * keyword_weight)
                result['hybrid_score'] = round(hybrid_score, 4)
                final_results.append(result)

            # Sort by hybrid score and limit results
            final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
            return final_results[:limit]

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np

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

# Global instance
vector_store = VectorStore()