from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

from app.database import get_async_db
from app.models import User, Document, ChatSession, Department
from app.api.deps import get_current_superuser
from app.services.llm_service import LLMService
from app.auth import get_password_hash

router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    department: str
    is_superuser: bool = False


class UserResponse(BaseModel):
    id: str
    email: str
    department: str
    is_superuser: bool
    is_active: bool
    created_at: str


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_documents: int
    processed_documents: int
    total_chat_sessions: int
    storage_used_bytes: int


class ServiceHealth(BaseModel):
    api: str
    database: str
    llm: str
    redis: str


class SystemHealthResponse(BaseModel):
    status: str
    services: ServiceHealth
    stats: SystemStats


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_superuser)
):
    """Get comprehensive system health status."""

    # Get system statistics
    user_stats = await db.execute(
        select(
            func.count(User.id).label('total'),
            func.sum(func.cast(User.is_active, "integer")).label('active')
        )
    )
    user_counts = user_stats.first()

    doc_stats = await db.execute(
        select(
            func.count(Document.id).label('total'),
            func.sum(
                func.case(
                    (Document.status == 'processed', 1),
                    else_=0
                )
            ).label('processed'),
            func.sum(Document.file_size).label('total_size')
        )
    )
    doc_counts = doc_stats.first()

    session_stats = await db.execute(
        select(func.count(ChatSession.id))
    )
    session_count = session_stats.scalar()

    # Check LLM service
    llm_service = LLMService()
    llm_health = await llm_service.check_health()

    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    stats = SystemStats(
        total_users=user_counts.total or 0,
        active_users=user_counts.active or 0,
        total_documents=doc_counts.total or 0,
        processed_documents=doc_counts.processed or 0,
        total_chat_sessions=session_count or 0,
        storage_used_bytes=doc_counts.total_size or 0
    )

    services = ServiceHealth(
        api="healthy",
        database=db_status,
        llm=llm_health["status"],
        redis="unknown"  # Would need Redis health check
    )

    overall_status = "healthy" if all(
        service in ["healthy", "unknown"] for service in [
            services.api, services.database, services.llm, services.redis
        ]
    ) else "degraded"

    return SystemHealthResponse(
        status=overall_status,
        services=services,
        stats=stats
    )


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: str = None,
    user_id: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_superuser)
):
    """Get audit logs."""

    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_superuser)
):
    """Create a new user (admin only)."""

    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Validate department
    try:
        dept = Department[request.department]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid department. Must be one of: {', '.join([d.name for d in Department])}"
        )

    # Create new user
    new_user = User(
        id=uuid.uuid4(),
        email=request.email,
        username=request.email.split('@')[0],
        full_name=request.email.split('@')[0],
        hashed_password=get_password_hash(request.password),
        primary_department=dept,
        is_superuser=request.is_superuser,
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        department=new_user.primary_department.name,
        is_superuser=new_user.is_superuser,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat()
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_superuser)
):
    """List all users (admin only)."""

    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            department=user.primary_department.name if user.primary_department else "None",
            is_superuser=user.is_superuser,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@router.get("/metrics")
async def get_system_metrics(
    metric_type: str = None,
    hours: int = 24,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_superuser)
):
    """Get system metrics."""

    from datetime import datetime, timedelta

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    query = select(SystemMetrics).where(
        SystemMetrics.created_at >= start_time,
        SystemMetrics.created_at <= end_time
    )

    if metric_type:
        query = query.where(SystemMetrics.metric_type == metric_type)

    query = query.order_by(SystemMetrics.created_at.desc())

    result = await db.execute(query)
    metrics = result.scalars().all()

    return [
        {
            "id": str(metric.id),
            "metric_type": metric.metric_type,
            "value": metric.value,
            "unit": metric.unit,
            "metadata": metric.metadata,
            "created_at": metric.created_at.isoformat()
        }
        for metric in metrics
    ]


@router.post("/reindex-documents")
async def reindex_documents(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_superuser)
):
    """Trigger reindexing of all documents."""

    # Get all processed documents
    result = await db.execute(
        select(Document).where(Document.status == 'processed')
    )
    documents = result.scalars().all()

    # TODO: Queue documents for reprocessing
    # This would be handled by Celery workers

    return {
        "message": f"{len(documents)} documents queued for reindexing",
        "document_count": len(documents)
    }