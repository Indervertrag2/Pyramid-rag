from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_, or_, func
from sqlalchemy.dialects.postgresql import ARRAY
import numpy as np

from app.models import Document, DocumentChunk, Tag, DocumentScope, SearchMode
from app.services.embedding_service import EmbeddingService
# from app.core.config import settings


class SearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def search(
        self,
        db: AsyncSession,
        query: str,
        user,
        mode: SearchMode = SearchMode.HYBRID,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        min_score: float = 0.5
    ) -> Dict[str, Any]:
        """Perform search based on the specified mode."""

        if mode == SearchMode.VECTOR:
            results = await self.vector_search(
                db, query, user, scope, department, limit, offset, min_score
            )
        elif mode == SearchMode.KEYWORD:
            results = await self.keyword_search(
                db, query, user, scope, department, limit, offset
            )
        else:  # HYBRID
            results = await self.hybrid_search(
                db, query, user, scope, department, limit, offset, min_score
            )

        return {
            "query": query,
            "mode": mode.value,
            "total_results": len(results),
            "results": results,
            "limit": limit,
            "offset": offset
        }

    async def vector_search(
        self,
        db: AsyncSession,
        query: str,
        user,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search using embeddings."""

        # Generate query embedding
        query_embedding = self.embedding_service.generate_query_embedding(query)

        # Build base query with access control
        base_query = await self._build_access_controlled_query(
            db, user, scope, department
        )

        # Perform vector search using pgvector
        # Using cosine similarity (1 - cosine_distance)
        vector_query = text("""
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                1 - (dc.embedding <=> :query_embedding::vector) as similarity,
                d.title,
                d.filename,
                d.scope,
                d.department,
                d.created_at
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE
                1 - (dc.embedding <=> :query_embedding::vector) >= :min_score
                AND d.id IN :allowed_docs
            ORDER BY similarity DESC
            LIMIT :limit OFFSET :offset
        """)

        # Get allowed document IDs based on access control
        allowed_docs = await self._get_allowed_document_ids(
            db, user, scope, department
        )

        result = await db.execute(
            vector_query,
            {
                "query_embedding": query_embedding.tolist(),
                "min_score": min_score,
                "allowed_docs": allowed_docs,
                "limit": limit,
                "offset": offset
            }
        )

        rows = result.fetchall()

        # Format results
        results = []
        for row in rows:
            results.append({
                "chunk_id": str(row.id),
                "document_id": str(row.document_id),
                "chunk_index": row.chunk_index,
                "content": row.content[:500],  # Preview
                "similarity_score": float(row.similarity),
                "document_title": row.title,
                "filename": row.filename,
                "scope": row.scope,
                "department": row.department,
                "created_at": row.created_at.isoformat()
            })

        return results

    async def keyword_search(
        self,
        db: AsyncSession,
        query: str,
        user,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Perform full-text keyword search."""

        # Prepare search query for PostgreSQL full-text search
        search_query = func.plainto_tsquery('german', query)

        # Build query with access control
        stmt = select(
            Document,
            func.ts_rank(
                func.to_tsvector('german', Document.content),
                search_query
            ).label('rank')
        ).where(
            func.to_tsvector('german', Document.content).op('@@')(search_query)
        )

        # Apply access control
        stmt = await self._apply_access_control(stmt, user, scope, department)

        # Order by relevance and apply pagination
        stmt = stmt.order_by(text('rank DESC')).limit(limit).offset(offset)

        result = await db.execute(stmt)
        rows = result.all()

        # Format results
        results = []
        for row in rows:
            doc = row[0]
            rank = row[1]

            # Highlight matching text
            highlighted = await self._highlight_matches(doc.content, query)

            results.append({
                "document_id": str(doc.id),
                "title": doc.title,
                "filename": doc.filename,
                "content_preview": highlighted[:500],
                "relevance_score": float(rank),
                "scope": doc.scope,
                "department": doc.department,
                "created_at": doc.created_at.isoformat()
            })

        return results

    async def hybrid_search(
        self,
        db: AsyncSession,
        query: str,
        user,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Combine vector and keyword search with score fusion."""

        # Perform both searches
        vector_results = await self.vector_search(
            db, query, user, scope, department, limit * 2, 0, min_score
        )

        keyword_results = await self.keyword_search(
            db, query, user, scope, department, limit * 2, 0
        )

        # Combine and rerank results using Reciprocal Rank Fusion (RRF)
        combined_results = self._reciprocal_rank_fusion(
            vector_results, keyword_results
        )

        # Apply pagination
        paginated_results = combined_results[offset:offset + limit]

        return paginated_results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Combine results using Reciprocal Rank Fusion."""

        scores = {}

        # Process vector search results
        for i, result in enumerate(vector_results):
            doc_id = result.get("document_id") or result.get("chunk_id")
            if doc_id not in scores:
                scores[doc_id] = {
                    "result": result,
                    "rrf_score": 0,
                    "vector_rank": i + 1,
                    "keyword_rank": None
                }
            scores[doc_id]["rrf_score"] += 1 / (k + i + 1)
            scores[doc_id]["vector_rank"] = i + 1

        # Process keyword search results
        for i, result in enumerate(keyword_results):
            doc_id = result["document_id"]
            if doc_id not in scores:
                scores[doc_id] = {
                    "result": result,
                    "rrf_score": 0,
                    "vector_rank": None,
                    "keyword_rank": i + 1
                }
            scores[doc_id]["rrf_score"] += 1 / (k + i + 1)
            scores[doc_id]["keyword_rank"] = i + 1

        # Sort by RRF score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )

        # Format final results
        final_results = []
        for item in sorted_results:
            result = item["result"].copy()
            result["hybrid_score"] = item["rrf_score"]
            result["vector_rank"] = item["vector_rank"]
            result["keyword_rank"] = item["keyword_rank"]
            final_results.append(result)

        return final_results

    async def _build_access_controlled_query(
        self,
        db: AsyncSession,
        user,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None
    ):
        """Build query with access control filters."""

        conditions = []

        # Superuser can see everything
        if not user.is_superuser:
            # Personal documents
            personal_condition = and_(
                Document.scope == DocumentScope.PERSONAL.value,
                Document.owner_id == user.id
            )

            # Department documents
            dept_condition = and_(
                Document.scope == DocumentScope.DEPARTMENT.value,
                Document.department.in_([user.primary_department] + [d.value for d in user.departments])
            )

            # Company documents
            company_condition = Document.scope == DocumentScope.COMPANY.value

            conditions.append(or_(personal_condition, dept_condition, company_condition))

        # Apply scope filter if specified
        if scope:
            conditions.append(Document.scope == scope.value)

        # Apply department filter if specified
        if department:
            conditions.append(Document.department == department)

        return conditions

    async def _apply_access_control(
        self,
        stmt,
        user,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None
    ):
        """Apply access control filters to a query."""

        conditions = await self._build_access_controlled_query(
            None, user, scope, department
        )

        for condition in conditions:
            stmt = stmt.where(condition)

        return stmt

    async def _get_allowed_document_ids(
        self,
        db: AsyncSession,
        user,
        scope: Optional[DocumentScope] = None,
        department: Optional[str] = None
    ) -> List[str]:
        """Get list of document IDs user has access to."""

        stmt = select(Document.id)
        stmt = await self._apply_access_control(stmt, user, scope, department)

        result = await db.execute(stmt)
        return [str(row[0]) for row in result.all()]

    async def _highlight_matches(
        self,
        text: str,
        query: str,
        max_length: int = 500
    ) -> str:
        """Highlight matching terms in text."""

        # Simple highlighting - in production, use PostgreSQL's ts_headline
        query_terms = query.lower().split()
        highlighted = text

        for term in query_terms:
            # Find term position
            pos = highlighted.lower().find(term)
            if pos >= 0:
                # Get surrounding context
                start = max(0, pos - 100)
                end = min(len(highlighted), pos + len(term) + 100)
                snippet = highlighted[start:end]

                # Add highlighting
                snippet = snippet.replace(
                    term,
                    f"**{term}**",
                    1  # Only highlight first occurrence
                )

                return f"...{snippet}..." if start > 0 else f"{snippet}..."

        # If no match found, return beginning of text
        return text[:max_length] + "..." if len(text) > max_length else text

    async def get_similar_documents(
        self,
        db: AsyncSession,
        document_id: str,
        user,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find documents similar to a given document."""

        # Get document chunks
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        # Average embeddings of all chunks
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
        if not embeddings:
            return []

        avg_embedding = np.mean(embeddings, axis=0)

        # Find similar documents
        vector_query = text("""
            SELECT DISTINCT ON (d.id)
                d.id,
                d.title,
                d.filename,
                1 - (dc.embedding <=> :query_embedding::vector) as similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE
                d.id != :exclude_id
                AND d.id IN :allowed_docs
            ORDER BY d.id, similarity DESC
            LIMIT :limit
        """)

        allowed_docs = await self._get_allowed_document_ids(db, user)

        result = await db.execute(
            vector_query,
            {
                "query_embedding": avg_embedding.tolist(),
                "exclude_id": document_id,
                "allowed_docs": allowed_docs,
                "limit": limit
            }
        )

        rows = result.fetchall()

        results = []
        for row in rows:
            results.append({
                "document_id": str(row.id),
                "title": row.title,
                "filename": row.filename,
                "similarity_score": float(row.similarity)
            })

        return results