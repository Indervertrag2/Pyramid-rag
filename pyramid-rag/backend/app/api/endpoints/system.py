from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Dict, Any
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.models import User, Document, ChatSession, ChatMessage, DocumentChunk
from app.auth import get_current_user as auth_get_current_user
from app.schemas import HealthCheckResponse, SystemStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Dependency to get current user
async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    user = auth_get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return user


# Root endpoint
@router.get("/")
async def root():
    return {
        "name": "Pyramid RAG Platform",
        "version": "1.0.0",
        "status": "running"
    }


# Health check
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    try:
        # Check database
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    return HealthCheckResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version="1.0.0",
        services={
            "api": "healthy",
            "database": db_status,
            "vector_store": "healthy",
            "ollama": "healthy"
        }
    )


# Detailed system health endpoint
@router.get("/api/v1/system/health")
async def system_health(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Detailed system health information (requires authentication)"""
    import psutil

    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "components": {}
    }

    # Database health
    try:
        result = db.execute(text("SELECT version()"))
        db_version = result.scalar()

        # Get database size
        db_size = db.execute(text("""
            SELECT pg_database_size('pyramid_rag') / 1024 / 1024 as size_mb
        """)).scalar()

        # Get connection count
        conn_count = db.execute(text("""
            SELECT count(*) FROM pg_stat_activity
            WHERE datname = 'pyramid_rag'
        """)).scalar()

        health_status["components"]["database"] = {
            "status": "healthy",
            "version": db_version,
            "size_mb": float(db_size) if db_size else 0,
            "active_connections": conn_count
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Ollama LLM health
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            ollama_response = await client.get("http://ollama:11434/api/tags")
            if ollama_response.status_code == 200:
                models = ollama_response.json().get("models", [])
                health_status["components"]["llm"] = {
                    "status": "healthy",
                    "available_models": [m["name"] for m in models],
                    "model_count": len(models)
                }
            else:
                health_status["components"]["llm"] = {
                    "status": "unhealthy",
                    "error": f"HTTP {ollama_response.status_code}"
                }
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["llm"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # System resources
    try:
        health_status["components"]["system"] = {
            "status": "healthy",
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
                "percent": psutil.disk_usage('/').percent
            }
        }

        # Alert if resources are critical
        if psutil.virtual_memory().percent > 90:
            health_status["components"]["system"]["status"] = "warning"
            health_status["status"] = "degraded"
        if psutil.disk_usage('/').percent > 90:
            health_status["components"]["system"]["status"] = "critical"
            health_status["status"] = "unhealthy"

    except Exception as e:
        health_status["components"]["system"]["error"] = str(e)

    # Document processing status
    try:
        total_docs = db.query(Document).count()
        processed_docs = db.query(Document).filter(Document.processed == True).count()
        failed_docs = db.query(Document).filter(Document.error_message != None).count()

        health_status["components"]["document_processor"] = {
            "status": "healthy" if failed_docs == 0 else "warning",
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "failed_documents": failed_docs,
            "processing_rate": f"{(processed_docs/total_docs*100):.1f}%" if total_docs > 0 else "N/A"
        }
    except Exception as e:
        health_status["components"]["document_processor"] = {
            "status": "error",
            "error": str(e)
        }

    # Vector store health
    try:
        chunk_count = db.query(DocumentChunk).count()
        chunks_with_embeddings = db.execute(text("""
            SELECT COUNT(*) FROM document_chunks
            WHERE embedding IS NOT NULL
        """)).scalar()

        health_status["components"]["vector_store"] = {
            "status": "healthy",
            "total_chunks": chunk_count,
            "chunks_with_embeddings": chunks_with_embeddings,
            "embedding_coverage": f"{(chunks_with_embeddings/chunk_count*100):.1f}%" if chunk_count > 0 else "N/A"
        }
    except Exception as e:
        health_status["components"]["vector_store"] = {
            "status": "error",
            "error": str(e)
        }

    return health_status


# System metrics endpoint for monitoring
@router.get("/api/v1/system/metrics")
async def system_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get system metrics in Prometheus format (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    metrics = []

    # Database metrics
    try:
        db_size = db.execute(text("""
            SELECT pg_database_size('pyramid_rag') as size
        """)).scalar()
        metrics.append(f"pyramid_database_size_bytes {db_size}")

        conn_count = db.execute(text("""
            SELECT count(*) FROM pg_stat_activity WHERE datname = 'pyramid_rag'
        """)).scalar()
        metrics.append(f"pyramid_database_connections {conn_count}")

        # Document metrics
        total_docs = db.query(Document).count()
        processed_docs = db.query(Document).filter(Document.processed == True).count()
        failed_docs = db.query(Document).filter(Document.error_message != None).count()

        metrics.append(f"pyramid_documents_total {total_docs}")
        metrics.append(f"pyramid_documents_processed {processed_docs}")
        metrics.append(f"pyramid_documents_failed {failed_docs}")

        # User metrics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.is_superuser == True).count()

        metrics.append(f"pyramid_users_total {total_users}")
        metrics.append(f"pyramid_users_active {active_users}")
        metrics.append(f"pyramid_users_admin {admin_users}")

        # Chat metrics
        total_sessions = db.query(ChatSession).count()
        total_messages = db.query(ChatMessage).count()

        metrics.append(f"pyramid_chat_sessions_total {total_sessions}")
        metrics.append(f"pyramid_chat_messages_total {total_messages}")

        # Vector store metrics
        total_chunks = db.query(DocumentChunk).count()
        chunks_with_embeddings = db.execute(text("""
            SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL
        """)).scalar()

        metrics.append(f"pyramid_chunks_total {total_chunks}")
        metrics.append(f"pyramid_chunks_with_embeddings {chunks_with_embeddings}")

    except Exception as e:
        metrics.append(f"# Error collecting metrics: {str(e)}")

    # System resource metrics
    try:
        import psutil
        metrics.append(f"pyramid_system_cpu_percent {psutil.cpu_percent()}")
        metrics.append(f"pyramid_system_memory_percent {psutil.virtual_memory().percent}")
        metrics.append(f"pyramid_system_disk_percent {psutil.disk_usage('/').percent}")
    except:
        pass

    return PlainTextResponse("\n".join(metrics), media_type="text/plain")


# Prometheus-compatible metrics endpoint (no auth) for Prometheus scrape
@router.get("/metrics")
async def metrics(db: Session = Depends(get_db)):
    """Expose selected metrics in Prometheus text format (no auth).
    Intended for internal scraping by Prometheus in the Docker network."""
    metrics = []
    try:
        # Basic DB metrics
        try:
            db_size = db.execute(text("""
                SELECT pg_database_size('pyramid_rag') as size
            """)).scalar()
            metrics.append(f"pyramid_database_size_bytes {db_size}")
        except Exception:
            pass

        # Counts
        try:
            total_docs = db.query(Document).count()
            metrics.append(f"pyramid_documents_total {total_docs}")
        except Exception:
            pass

        try:
            total_users = db.query(User).count()
            metrics.append(f"pyramid_users_total {total_users}")
        except Exception:
            pass

        # System resource metrics
        try:
            import psutil
            metrics.append(f"pyramid_system_cpu_percent {psutil.cpu_percent()}")
            metrics.append(f"pyramid_system_memory_percent {psutil.virtual_memory().percent}")
        except Exception:
            pass
    finally:
        return PlainTextResponse("\n".join(metrics) + "\n", media_type="text/plain")


# System stats endpoint
@router.get("/api/v1/system/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Calculate stats
    from datetime import timedelta

    total_documents = db.query(Document).count()
    total_users = db.query(User).count()

    # Documents this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    documents_this_week = db.query(Document).filter(
        Document.created_at >= week_ago
    ).count()

    # Active chats
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    active_chats = db.query(ChatSession).filter(
        ChatSession.updated_at >= hour_ago
    ).count()

    # Storage (mock for now)
    import random
    storage_used = random.uniform(40, 80)
    storage_total = 100

    return SystemStatsResponse(
        total_documents=total_documents,
        total_users=total_users,
        documents_this_week=documents_this_week,
        active_chats=active_chats,
        storage_used_gb=storage_used,
        storage_total_gb=storage_total
    )
