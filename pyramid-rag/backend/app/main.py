from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uvicorn
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
import time

from app.database import get_db, init_db
from app.models import (
    User,
    Document,
    ChatSession,
    ChatMessage,
    DocumentChunk,
    DocumentEmbedding,
    Department,
    FileType,
    ChatFile,
    ChatType,
    FileScope,
)
from app.schemas import (
    LoginRequest, TokenResponse, UserResponse, UserCreate, UserUpdate, UserCreateRequest,
    DocumentResponse, DocumentListResponse, DocumentCreate,
    ChatMessageRequest, ChatMessageResponse, ChatSessionResponse,
    SearchRequest, SearchResponse, SearchResultItem,
    SystemStatsResponse, HealthCheckResponse,
    DepartmentEnum, FileTypeEnum,
    ChatSessionCreateRequest, ChatSessionUpdateRequest, ChatFileResponse, ChatFileDetailResponse, ChatTypeEnum, FileScopeEnum
)
from app.auth import (
    authenticate_user, create_access_token, create_refresh_token,
    get_current_user, create_user as auth_create_user, get_password_hash
)
from app.services.document_processor import document_processor
from app.services.upload_response import prepare_upload_response
from app.services.text_utils import sanitize_document_text
import shutil
from pathlib import Path
import uuid
import logging

logger = logging.getLogger(__name__)

# Create upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Pyramid RAG Platform",
    version="1.0.0",
    description="Enterprise RAG Platform fÃ¼r Pyramid Computer GmbH"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:4000",
        "http://localhost:8080",
        "http://localhost:18000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Dependency to get current user
async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    user = get_current_user(db, token)
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
@app.get("/")
async def root():
    return {
        "name": "Pyramid RAG Platform",
        "version": "1.0.0",
        "status": "running"
    }

# Health check
@app.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    try:
        # Check database
        from sqlalchemy import text
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
@app.get("/api/v1/system/health")
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
@app.get("/api/v1/system/metrics")
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
@app.get("/metrics")
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

# Authentication endpoints
@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or username already exists"
        )

    user = auth_create_user(
        db,
        email=user_data.email,
        password=user_data.password,
        username=user_data.username,
        full_name=user_data.full_name,
        department=user_data.primary_department
    )

    return UserResponse.from_orm(user)

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UngÃ¼ltige E-Mail oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user)
    )

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse.from_orm(current_user)

# Document endpoints

@app.get("/api/v1/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department: Optional[DepartmentEnum] = None,
    file_type: Optional[FileTypeEnum] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(Document)

    # Apply visibility-based access control
    if not current_user.is_superuser and current_user.primary_department != Department.MANAGEMENT:
        # Non-Management users see:
        # 1. Documents with visibility="all"
        # 2. Documents from their department with visibility="department"
        # 3. Their own uploaded documents
        from sqlalchemy import cast, func
        from sqlalchemy.dialects.postgresql import JSONB

        query = query.filter(
            (cast(Document.meta_data, JSONB)["visibility"].astext == "all") |
            ((cast(Document.meta_data, JSONB)["visibility"].astext == "department") &
             (Document.department == current_user.primary_department)) |
            (Document.uploaded_by == current_user.id)
        )
    # Management and Superusers can see everything (no filter needed)

    if department:
        query = query.filter(Document.department == Department[department])

    if file_type:
        query = query.filter(Document.file_type == FileType[file_type.upper()])

    # Pagination
    total = query.count()
    documents = query.offset((page - 1) * page_size).limit(page_size).all()

    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size
    )

@app.get("/api/v1/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check access
    if not current_user.is_superuser:
        if document.department != current_user.primary_department and document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    return DocumentResponse.from_orm(document)

# NEW RAG-enabled Upload API
# Created: 2025-09-26 09:00 UTC


@app.get("/api/v1/chat/files/{file_id}", response_model=ChatFileDetailResponse)
async def get_chat_file_detail(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    chat_file = db.query(ChatFile).filter(ChatFile.id == file_id).first()

    if not chat_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat file not found"
        )

    if not current_user.is_superuser and chat_file.session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    file_type_value = chat_file.file_type.value if chat_file.file_type else FileType.OTHER.value
    scope_value = chat_file.scope.value if chat_file.scope else FileScope.CHAT.value
    full_content = chat_file.content or ""
    sanitized_content = sanitize_document_text(full_content)
    content_length = len(sanitized_content)
    content_preview = sanitized_content[:200] + "..." if content_length > 200 else sanitized_content
    content_excerpt = sanitized_content[:8000]

    return ChatFileDetailResponse(
        id=chat_file.id,
        filename=chat_file.filename,
        original_filename=chat_file.original_filename,
        file_type=file_type_value,
        file_size=chat_file.file_size or 0,
        title=chat_file.title,
        description=chat_file.description,
        scope=scope_value,
        save_to_company=chat_file.save_to_company,
        processed=chat_file.processed,
        processing_error=chat_file.processing_error,
        created_at=chat_file.created_at,
        updated_at=chat_file.updated_at,
        mime_type=chat_file.mime_type,
        file_hash=chat_file.file_hash,
        content=content_excerpt,
        content_preview=content_preview,
        content_length=content_length,
        language=chat_file.language,
        meta_data=chat_file.meta_data or {}
    )


@app.post("/api/v1/documents/upload")
async def upload_document_unified(
    file: UploadFile = File(...),
    scope: FileScopeEnum = Form(FileScopeEnum.GLOBAL),  # File scope toggle: GLOBAL vs CHAT
    visibility: str = Form("department"),  # "all" or "department" - who can see the file
    session_id: Optional[str] = Form(None),  # Required for CHAT scope
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ðŸš€ NEW UNIFIED UPLOAD API (2025) - Advanced RAG Pipeline

    Features:
    - SHA-256 deduplication prevents duplicate files
    - Automatic metadata extraction (no user input required)
    - Multi-format support: PDF, DOCX, XLSX, PPTX, Images, Text
    - Intelligent text chunking optimized for RAG
    - Multilingual embedding generation (German + English optimized)
    - File scope toggle: Company database vs Chat-only
    - OCR support for scanned documents (when available)
    """

    # Validate scope and session
    if scope == FileScopeEnum.CHAT and not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id required for CHAT scope files"
        )

    if scope == FileScopeEnum.CHAT:
        # Validate chat session exists and belongs to user
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

    # Create unique file path
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    saved_filename = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / saved_filename

    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File save failed: {str(e)}"
        )

    try:
        # ðŸ”¥ PROCESS WITH ADVANCED DOCUMENT PROCESSOR (2025)
        processing_result = await document_processor.process_document(
            file_path=file_path,
            original_filename=file.filename or "unknown",
            scope=scope
        )

        if not processing_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Document processing failed: {processing_result.get('errors', 'Unknown error')}"
            )

        # Check for duplicate based on SHA-256 hash
        file_hash = processing_result["file_hash"]

        if scope == FileScopeEnum.GLOBAL:
            # Check for duplicate in Document table (only for global files)
            existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
            if existing_doc:
                # Remove uploaded file since it's a duplicate
                os.remove(file_path)
                return {
                    "duplicate": True,
                    "existing_document_id": str(existing_doc.id),
                    "message": f"File already exists: {existing_doc.filename}",
                    "filename": existing_doc.filename,
                    "created_at": existing_doc.created_at.isoformat()
                }

        response_metadata = processing_result.get("metadata") if isinstance(processing_result.get("metadata"), dict) else {}
        visibility_normalized = (visibility or "department").lower()

        if scope == FileScopeEnum.GLOBAL:
            # Store in company database (Document table)
            enhanced_metadata = dict(response_metadata)
            enhanced_metadata["visibility"] = visibility_normalized
            enhanced_metadata["uploaded_by_department"] = current_user.primary_department.value
            enhanced_metadata["uploaded_by_email"] = current_user.email
            if visibility_normalized == "all":
                enhanced_metadata["allowed_departments"] = ["ALL"]
            else:
                enhanced_metadata["allowed_departments"] = [current_user.primary_department.value]

            embedding_model_name = enhanced_metadata.get("embedding_model", "paraphrase-multilingual-mpnet-base-v2")

            document = Document(
                id=uuid.uuid4(),
                filename=saved_filename,
                original_filename=file.filename or "unknown",
                file_path=str(file_path),
                file_type=processing_result["file_type"],
                file_size=os.path.getsize(file_path),
                mime_type=processing_result["mime_type"],
                file_hash=file_hash,
                title=enhanced_metadata.get("title", file.filename),
                content=processing_result["content"],
                language=processing_result["language"],
                meta_data=enhanced_metadata,
                department=current_user.primary_department,
                uploaded_by=current_user.id,
                processed=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            chunks = processing_result.get("chunks") or []
            chunk_records: List[DocumentChunk] = []
            if chunks:
                for i, chunk_info in enumerate(chunks):
                    chunk = DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=document.id,
                        chunk_index=i,
                        content=chunk_info["content"],
                        content_length=chunk_info["character_count"],
                        meta_data={
                            "word_count": chunk_info["word_count"],
                            "start_word": chunk_info.get("start_word"),
                            "end_word": chunk_info.get("end_word"),
                        },
                        token_count=chunk_info["word_count"],
                        created_at=datetime.utcnow()
                    )
                    db.add(chunk)
                    chunk_records.append(chunk)

                db.flush()

                embeddings = processing_result.get("embeddings") or []
                if embeddings:
                    for chunk_obj, embedding_vector in zip(chunk_records, embeddings):
                        embedding_record = DocumentEmbedding(
                            id=uuid.uuid4(),
                            document_id=document.id,
                            chunk_id=chunk_obj.id,
                            embedding=embedding_vector,
                            model_name=embedding_model_name
                        )
                        db.add(embedding_record)

                db.commit()

            response_metadata = enhanced_metadata

        else:
            # Store as chat file (ChatFile table)
            chat_metadata = dict(response_metadata)
            chat_file = ChatFile(
                id=uuid.uuid4(),
                session_id=session_id,
                filename=saved_filename,
                original_filename=file.filename or "unknown",
                file_path=str(file_path),
                file_type=processing_result["file_type"],
                file_size=os.path.getsize(file_path),
                mime_type=processing_result["mime_type"],
                file_hash=file_hash,
                title=chat_metadata.get("title", file.filename),
                content=processing_result["content"],
                language=processing_result["language"],
                meta_data=chat_metadata,
                scope=scope,
                uploaded_by=current_user.id,
                processed=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(chat_file)
            db.commit()
            db.refresh(chat_file)
            document = chat_file  # For consistent return
            response_metadata = chat_metadata

        return prepare_upload_response(
            document=document,
            processing_result=processing_result,
            metadata=response_metadata,
            scope=scope,
            current_user=current_user,
            session_id=session_id,
        )


    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            os.remove(file_path)
        logger.error(f"Upload processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )

# ðŸ—‘ï¸ OLD ENDPOINTS REMOVED - Now using MCP
# The /api/v1/chat endpoint has been replaced by /api/v1/mcp/message
# which provides better standardization through Model Context Protocol

# DEPRECATED - Remove this entire chat endpoint as it's replaced by MCP
"""
@app.post("/api/v1/chat", response_model=ChatMessageResponse)
async def chat_old_deprecated(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Debug logging
    print(f"DEBUG: Chat request received - content: '{request.content}', session_id: {request.session_id}, rag_enabled: {request.rag_enabled}, uploaded_docs: {len(request.uploaded_documents)}")

    # Process document context for RAG
    document_context = ""
    sources = []

    if request.rag_enabled:
        # Use vector search to find relevant documents from the database
        from app.vector_store import vector_store

        try:
            # Perform hybrid search to get relevant document chunks
            search_results = await vector_store.hybrid_search(
                query=request.content,
                db=db,
                limit=5,  # Get top 5 most relevant chunks
                user_department=current_user.primary_department.value if current_user.primary_department else None
            )

            if search_results:
                document_context += "\n\n--- RELEVANTE DOKUMENTE AUS DER WISSENSDATENBANK ---\n"
                for result in search_results:
                    document_context += f"\nQUELLE: {result['document_title']} (Relevanz: {result.get('hybrid_score', 0):.2f})\n"
                    document_context += f"INHALT: {result['chunk_content'][:1000]}{'...' if len(result['chunk_content']) > 1000 else ''}\n"
                    document_context += "---\n"

                    # Collect sources for response metadata
                    sources.append({
                        "document_id": result['document_id'],
                        "chunk_id": result['chunk_id'],
                        "title": result['document_title'],
                        "filename": result['document_filename'],
                        "relevance_score": result.get('hybrid_score', 0),
                        "chunk_index": result['chunk_index']
                    })

                print(f"DEBUG: Found {len(search_results)} relevant document chunks via vector search")
            else:
                print("DEBUG: No relevant documents found in vector search")

        except Exception as e:
            print(f"DEBUG: Vector search error: {e}")
            # Continue without vector search results

    # Process uploaded documents content (in addition to vector search results)
    if request.uploaded_documents:
        if not document_context:
            document_context = ""
        document_context += "\n\n--- HOCHGELADENE DOKUMENTE ---\n"
        for doc in request.uploaded_documents:
            document_context += f"\nDATEI: {doc.title}\n"
            if doc.content:
                document_context += f"INHALT: {doc.content[:2000]}{'...' if len(doc.content) > 2000 else ''}\n"
            document_context += "---\n"

    # Get or create session
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
    else:
        session = ChatSession(
            user_id=current_user.id,
            title=request.content[:50]
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save user message
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.content
    )
    db.add(user_message)

    # Direct Ollama API call
    try:
        import httpx
        import asyncio

        async with httpx.AsyncClient(timeout=30.0) as client:
            ollama_response = await client.post(
                "http://ollama:11434/api/chat",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Du bist ein hilfreicher KI-Assistent fÃ¼r die Pyramid Computer GmbH. Antworte kurz und prÃ¤zise auf Deutsch. " +
                                     (f"RAG-Modus ist aktiviert - verwende das bereitgestellte Dokumentenwissen zur Beantwortung. Zitiere dabei die relevanten Quellen." if request.rag_enabled else "RAG-Modus ist deaktiviert - beantworte nur mit deinem allgemeinen Wissen, ohne Dokumentenkontext.") +
                                     (" Wenn du Informationen aus den Dokumenten verwendest, erwÃ¤hne die Quelle." if document_context else "")
                        },
                        {"role": "user", "content": f"{request.content}{document_context}"}
                    ],
                    "stream": False
                }
            )

            if ollama_response.status_code == 200:
                ollama_data = ollama_response.json()
                response_content = ollama_data.get("message", {}).get("content", "Keine Antwort generiert.")
            else:
                response_content = f"Ollama Fehler: {ollama_response.status_code}"

    except Exception as e:
        print(f"Ollama API error: {e}")
        response_content = f"Entschuldigung, es gab einen technischen Fehler. Bitte versuchen Sie es erneut."

    # Save assistant message with sources
    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_content,
        meta_data={"sources": sources, "rag_enabled": request.rag_enabled}
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatMessageResponse(
        id=assistant_message.id,
        role=assistant_message.role,
        content=assistant_message.content,
        created_at=assistant_message.created_at,
        sources=sources
    )
"""
# END OF DEPRECATED CHAT ENDPOINT

@app.get("/api/v1/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).limit(20).all()

    return [ChatSessionResponse.from_orm(session) for session in sessions]

# Search endpoints
@app.post("/api/v1/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    import time
    start_time = time.time()

    # Mock search for now
    query = db.query(Document)

    if not current_user.is_superuser:
        query = query.filter(Document.department == current_user.primary_department)

    if request.departments:
        query = query.filter(Document.department.in_([Department[d] for d in request.departments]))

    if request.file_types:
        query = query.filter(Document.file_type.in_([FileType[f.upper()] for f in request.file_types]))

    documents = query.limit(request.limit).offset(request.offset).all()

    # Format results
    search_results = []
    for doc in documents:
        search_results.append(SearchResultItem(
            document_id=doc.id,
            filename=doc.filename,
            title=doc.title,
            excerpt=doc.description[:200] if doc.description else "Keine Beschreibung verfÃ¼gbar",
            relevance_score=0.95,  # Mock score
            department=doc.department.value,
            file_type=doc.file_type.value
        ))

    took_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        results=search_results,
        total=len(search_results),
        query=request.query,
        took_ms=took_ms
    )

# System stats endpoint
@app.get("/api/v1/system/stats", response_model=SystemStatsResponse)
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

# Admin endpoints
@app.get("/api/v1/admin/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]

@app.post("/api/v1/admin/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create new user
    new_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.email.split('@')[0],
        full_name=user_data.email.split('@')[0],
        hashed_password=get_password_hash(user_data.password),
        primary_department=Department[user_data.department],
        is_superuser=user_data.is_superuser,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.from_orm(new_user)

@app.put("/api/v1/admin/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    for field, value in user_update.dict(exclude_unset=True).items():
        if field == "primary_department" and value:
            setattr(user, field, Department[value])
        else:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return UserResponse.from_orm(user)

# Additional admin endpoints for users management
@app.get("/api/v1/users", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]

@app.post("/api/v1/users", response_model=UserResponse)
async def create_user_endpoint(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    new_user = auth_create_user(
        db,
        email=user_data.email,
        password=user_data.password,
        username=user_data.username,
        full_name=user_data.full_name,
        department=Department(user_data.primary_department),
        is_superuser=user_data.is_superuser if hasattr(user_data, 'is_superuser') else False
    )

    return UserResponse.from_orm(new_user)

@app.patch("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user_patch(
    user_id: str,
    user_update: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user details (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update allowed fields
    allowed_fields = ['username', 'full_name', 'primary_department', 'is_active', 'is_superuser']
    for field, value in user_update.items():
        if field in allowed_fields:
            if field == 'primary_department':
                setattr(user, field, Department(value))
            else:
                setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return UserResponse.from_orm(user)

@app.delete("/api/v1/users/{user_id}")
async def delete_user_endpoint(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Don't delete the default admin
    if user.email == "admin@pyramid-computer.de":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system admin user"
        )

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# Admin stats endpoint
@app.get("/api/v1/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    total_users = db.query(User).count()
    total_documents = db.query(Document).count()
    total_chats = db.query(ChatSession).count()

    # Get processed vs unprocessed documents
    processed_docs = db.query(Document).filter(Document.processed == True).count()
    unprocessed_docs = total_documents - processed_docs

    # Get active users (logged in within last 7 days - would need to track last login)
    active_users = db.query(User).filter(User.is_active == True).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_documents": total_documents,
        "processed_documents": processed_docs,
        "unprocessed_documents": unprocessed_docs,
        "total_chats": total_chats,
        "departments": db.query(User.primary_department, func.count(User.id))
            .group_by(User.primary_department).all()
    }

# Document reprocessing endpoint
@app.post("/api/v1/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reprocess a document (regenerate chunks and embeddings)"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check permissions
    if not current_user.is_superuser and document.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to reprocess this document"
        )

    try:
        # Delete existing chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.commit()

        # Reprocess the document
        from app.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        await processor.process_document(str(document.id), db)

        return {"message": "Document reprocessing started", "document_id": str(document.id)}
    except Exception as e:
        logger.error(f"Error reprocessing document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocessing document: {str(e)}"
        )

# MCP Server endpoints

# Request model for MCP messages
class MCPQueryMode(str, Enum):
    HYBRID = "HYBRID"
    VECTOR = "VECTOR"
    KEYWORD = "KEYWORD"


class MCPUngatedSearchRequest(BaseModel):
    query: str
    mode: MCPQueryMode = MCPQueryMode.HYBRID
    limit: int = 5
    offset: int = 0
    department: Optional[str] = None


class MCPMessageRequest(BaseModel):
    messages: List[Dict[str, Any]]
    tools: Optional[List[str]] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@app.post("/api/v1/mcp/search")
async def mcp_search(
    request: MCPUngatedSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search documents via MCP-compatible response structure."""
    from app.vector_store import vector_store
    department_value = request.department or (current_user.primary_department.value if hasattr(current_user.primary_department, 'value') else str(current_user.primary_department))

    limit_for_query = max(request.limit, request.limit + request.offset)
    start_time = time.time()

    if request.mode == MCPQueryMode.VECTOR:
        raw_results = await vector_store.semantic_search(
            query=request.query,
            db=db,
            limit=limit_for_query,
            user_department=department_value
        )
    elif request.mode == MCPQueryMode.KEYWORD:
        raw_results = await vector_store.keyword_search(
            query=request.query,
            db=db,
            limit=limit_for_query,
            user_department=department_value
        )
    else:
        raw_results = await vector_store.hybrid_search(
            query=request.query,
            db=db,
            limit=limit_for_query,
            user_department=department_value
        )

    results = raw_results[request.offset:request.offset + request.limit]
    took_ms = int((time.time() - start_time) * 1000)

    return {
        "query": request.query,
        "mode": request.mode.value,
        "results": results,
        "total_results": len(raw_results),
        "took_ms": took_ms
    }


@app.post("/api/v1/mcp/message")
async def process_mcp_message(
    request: MCPMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Process MCP protocol message with enhanced functionality"""
    try:
        from app.mcp_server import ToolType, get_mcp_server, initialize_mcp_server

        # Generate session_id if not provided
        session_id = request.session_id or f"session_{current_user.id}_{datetime.now().timestamp()}"

        # Reuse MCP server instance to preserve session context
        mcp_server = get_mcp_server(db)
        if not mcp_server:
            mcp_server = await initialize_mcp_server(db)
        else:
            mcp_server.update_session(db)

        # Extract context from request
        context = request.context or {}
        rag_enabled = context.get('rag_enabled', True)
        uploaded_documents = context.get('uploaded_documents', [])

        # Process each message
        all_responses = []
        citations = []

        for msg in request.messages:
            message_payload = dict(msg)
            # Determine which tools to use
            if rag_enabled and request.tools and 'hybrid_search' in request.tools:
                # First, perform search
                department_value = current_user.primary_department.value if hasattr(current_user.primary_department, 'value') else str(current_user.primary_department)
                search_result = await mcp_server.tools[ToolType.HYBRID_SEARCH].execute(
                    query=msg['content'],
                    department=department_value,
                    limit=5
                )

                if search_result.get('success') and search_result.get('results'):
                    # Extract citations
                    for result in search_result['results']:
                        citations.append({
                            'document_id': result.get('document_id', ''),
                            'document_title': result.get('title', ''),
                            'snippet': result.get('text', '')[:200],
                            'relevance_score': result.get('score', 0.0)
                        })

                    # Add context to message
                    context_text = "\n\n".join([r.get('content', r.get('text', '')) for r in search_result['results'][:3]])
                    enhanced_content = f"Context:\n{context_text}\n\nUser Question: {msg['content']}"
                    message_payload['content'] = enhanced_content

            if uploaded_documents and 'uploaded_documents' not in message_payload:
                message_payload['uploaded_documents'] = uploaded_documents

            # Process message through chat
            response = await mcp_server.process_message(
                message=message_payload,
                session_id=session_id,
                user_id=str(current_user.id),
                department=department_value if 'department_value' in locals() else (current_user.primary_department.value if hasattr(current_user.primary_department, 'value') else str(current_user.primary_department))
            )

            all_responses.append(response)

        # Collect manual document citations from MCP context
        manual_context_citations: List[Dict[str, Any]] = []
        context_snapshot = getattr(mcp_server, "contexts", {}).get(session_id)
        if context_snapshot and getattr(context_snapshot, "documents", None):
            for doc_entry in context_snapshot.documents[-5:]:
                doc_id = doc_entry.get("id")
                content = doc_entry.get("content") or ""
                if not doc_id or not content:
                    continue
                manual_context_citations.append({
                    'document_id': doc_id,
                    'document_title': doc_entry.get('title', ''),
                    'snippet': content[:200],
                    'relevance_score': 1.0
                })

        final_citations = citations if rag_enabled else []
        existing_ids = {c.get('document_id') for c in final_citations if c.get('document_id')}
        for citation in manual_context_citations:
            if citation['document_id'] not in existing_ids:
                final_citations.append(citation)
                existing_ids.add(citation['document_id'])

        # Format response to match frontend expectations
        return {
            'success': True,
            'messages': [
                {
                    'role': 'assistant',
                    'content': all_responses[-1].get('content', '') if all_responses else 'Keine Antwort generiert.'
                }
            ],
            'citations': final_citations,
            'metadata': {
                'session_id': session_id,
                'rag_enabled': rag_enabled,
                'tools_used': request.tools
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/mcp/tools")
async def get_mcp_tools(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available MCP tools"""
    from app.mcp_server import get_mcp_server, initialize_mcp_server

    mcp_server = get_mcp_server(db)
    if not mcp_server:
        mcp_server = await initialize_mcp_server(db)

    return {
        "tools": mcp_server.get_available_tools()
    }

@app.get("/api/v1/mcp/context/{session_id}")
async def get_mcp_context(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get MCP context summary"""
    from app.mcp_server import get_mcp_server

    mcp_server = get_mcp_server(db)
    if not mcp_server:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP server not initialized"
        )

    context = mcp_server.get_context_summary(session_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )

    return context

@app.delete("/api/v1/mcp/context/{session_id}")
async def clear_mcp_context(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Clear MCP context"""
    from app.mcp_server import get_mcp_server

    mcp_server = get_mcp_server(db)
    if not mcp_server:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP server not initialized"
        )

    mcp_server.clear_context(session_id)
    return {"message": "Context cleared"}

@app.post("/api/v1/mcp/stream")
async def stream_mcp_chat(
    request: MCPMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Stream MCP chat responses using Server-Sent Events via MCP service"""
    import json
    import httpx

    async def event_generator():
        try:
            # Extract message and context
            last_message = request.messages[-1] if request.messages else {"content": ""}
            message_content = last_message.get("content", "")

            # Get department for context
            department_value = current_user.primary_department.value if hasattr(current_user.primary_department, 'value') else str(current_user.primary_department)

            # Build context
            context = request.context or {}
            context["department"] = department_value
            context["user_id"] = str(current_user.id)  # Convert UUID to string
            context["rag_enabled"] = context.get("rag_enabled", True)

            # Stream response from MCP service
            session_id = request.session_id or str(uuid.uuid4())

            # Optionally augment message with RAG context using internal MCPServer tools
            try:
                use_rag = context.get("rag_enabled", True) or (request.tools and ("hybrid_search" in request.tools or "document_search" in request.tools))
                if use_rag:
                    from app.mcp_server import MCPServer, ToolType
                    mcp_server = MCPServer(db)
                    # Perform hybrid search for best context
                    search_result = await mcp_server.tools[ToolType.HYBRID_SEARCH].execute(
                        query=message_content,
                        department=department_value,
                        limit=5
                    )
                    if search_result.get("success") and search_result.get("results"):
                        context_text = "\n\n".join([r.get("content", r.get("text", r.get("chunk_content", ""))) for r in search_result["results"][:3]])
                        context["search_results"] = search_result.get("results", [])
                        message_content = f"Context:\n{context_text}\n\nUser Question: {message_content}"
            except Exception as e:
                logger.warning(f"RAG context augmentation failed: {e}")

            # Call MCP service streaming endpoint
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    'http://pyramid-mcp:8001/mcp/stream',
                    json={
                        "message": message_content,
                        "session_id": session_id,
                        "context": context
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            # Parse SSE format
                            if line.startswith('event:'):
                                event_type = line[6:].strip()
                            elif line.startswith('data:'):
                                data_str = line[5:].strip()
                                if data_str:
                                    # Forward the event
                                    yield {
                                        "event": event_type if 'event_type' in locals() else "message",
                                        "data": data_str
                                    }

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    # Return as Server-Sent Events stream
    async def sse_generator():
        async for event in event_generator():
            if event['event'] == 'message':
                yield f"event: message\ndata: {event['data']}\n\n"
            elif event['event'] == 'done':
                yield f"event: done\ndata: {event['data']}\n\n"
            elif event['event'] == 'error':
                yield f"event: error\ndata: {event['data']}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.on_event("startup")
async def startup_event():
    """Initialize database and create default admin user"""
    init_db()

    # Create default admin user if not exists
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@pyramid-computer.de").first()
        if not admin:
            from app.models import Department
            auth_create_user(
                db,
                email="admin@pyramid-computer.de",
                password="admin123",
                username="admin",
                full_name="System Administrator",
                department=Department.MANAGEMENT,  # This is correct - MANAGEMENT = "Management"
                is_superuser=True
            )
            print("Default admin user created")
    finally:
        db.close()

# New Chat System API Endpoints

@app.post("/api/v2/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session_v2(
    request: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session (normal or temporary)"""
    from datetime import timedelta
    from app.models import ChatType

    expires_at = None
    if request.chat_type == ChatTypeEnum.TEMPORARY:
        # Temporary chats expire after 30 days from creation
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    session = ChatSession(
        user_id=current_user.id,
        title=request.title or "New Chat",
        chat_type=ChatType(request.chat_type.value),
        expires_at=expires_at,
        folder_path=request.folder_path
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return ChatSessionResponse.from_orm(session)

@app.get("/api/v2/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific chat session"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )

    return ChatSessionResponse.from_orm(session)

# ðŸ—‘ï¸ OLD UPLOAD ENDPOINT REMOVED
# Use /api/v1/documents/upload instead (unified upload system)

@app.delete("/api/v1/chat/cleanup-expired")
async def cleanup_expired_chats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cleanup expired temporary chats (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models import ChatType

    # Find expired chats
    now = datetime.now(timezone.utc)
    expired_chats = db.query(ChatSession).filter(
        ChatSession.chat_type == ChatType.TEMPORARY,
        ChatSession.expires_at < now
    ).all()

    deleted_count = 0
    for chat in expired_chats:
        # Delete associated files from disk
        chat_dir = f"data/chat_files/{chat.id}"
        if os.path.exists(chat_dir):
            import shutil
            shutil.rmtree(chat_dir)

        # Delete from database (cascade will handle related records)
        db.delete(chat)
        deleted_count += 1

    db.commit()

    return {"deleted_chats": deleted_count, "message": f"Cleaned up {deleted_count} expired chats"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
