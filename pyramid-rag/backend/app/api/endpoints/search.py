from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import SearchMode, DocumentScope
from app.api.deps import get_current_user
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str
    mode: SearchMode = SearchMode.HYBRID
    scope: Optional[DocumentScope] = None
    department: Optional[str] = None
    limit: int = 20
    offset: int = 0
    min_score: float = 0.5


class SearchResultItem(BaseModel):
    document_id: str
    title: str
    filename: str
    content_preview: str
    score: float
    scope: str
    department: Optional[str]
    created_at: str


class SearchResponse(BaseModel):
    query: str
    mode: str
    total_results: int
    results: List[SearchResultItem]
    processing_time: float


@router.post("/", response_model=SearchResponse)
async def search_documents(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search documents using the specified mode."""

    search_service = SearchService()

    import time
    start_time = time.time()

    search_results = await search_service.search(
        db=db,
        query=search_request.query,
        user=current_user,
        mode=search_request.mode,
        scope=search_request.scope,
        department=search_request.department,
        limit=search_request.limit,
        offset=search_request.offset,
        min_score=search_request.min_score
    )

    processing_time = time.time() - start_time

    # Convert results to response format
    result_items = []
    for result in search_results["results"]:
        result_items.append(
            SearchResultItem(
                document_id=result.get("document_id", ""),
                title=result.get("document_title", result.get("title", "")),
                filename=result.get("filename", ""),
                content_preview=result.get("content", result.get("content_preview", ""))[:500],
                score=result.get("similarity_score", result.get("relevance_score", result.get("hybrid_score", 0))),
                scope=result.get("scope", ""),
                department=result.get("department", ""),
                created_at=result.get("created_at", "")
            )
        )

    return SearchResponse(
        query=search_request.query,
        mode=search_request.mode.value,
        total_results=len(result_items),
        results=result_items,
        processing_time=processing_time
    )


@router.get("/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Find documents similar to the given document."""

    search_service = SearchService()

    similar_docs = await search_service.get_similar_documents(
        db=db,
        document_id=document_id,
        user=current_user,
        limit=limit
    )

    return {
        "document_id": document_id,
        "similar_documents": similar_docs
    }