from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import uuid
import os
import shutil
import logging

from app.database import get_db
from app.models import (
    User, Document, DocumentChunk, DocumentEmbedding,
    Department, FileType, ChatFile, FileScope
)
from app.schemas import (
    DocumentResponse, DocumentListResponse, DocumentCreate,
    DepartmentEnum, FileTypeEnum, FileScopeEnum,
    ChatFileDetailResponse
)
from app.auth import get_current_user as auth_get_current_user
from app.utils.file_security import sanitize_filename, secure_join

logger = logging.getLogger(__name__)

# Import heavy dependencies with logging
import time
start_time = time.time()
logger.info("Loading document processor (this may take a moment due to ML libraries)...")
from app.services.document_processor import document_processor
logger.info(f"Document processor loaded in {time.time() - start_time:.2f}s")

start_time = time.time()
logger.info("Loading upload response utilities...")
from app.services.upload_response import prepare_upload_response
logger.info(f"Upload response utilities loaded in {time.time() - start_time:.2f}s")

start_time = time.time()
logger.info("Loading text utilities...")
from app.services.text_utils import sanitize_document_text
logger.info(f"Text utilities loaded in {time.time() - start_time:.2f}s")

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

# Create upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


@router.get("", response_model=DocumentListResponse)
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


@router.get("/{document_id}", response_model=DocumentResponse)
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


@router.post("/upload")
async def upload_document_unified(
    file: UploadFile = File(...),
    scope: FileScopeEnum = Form(FileScopeEnum.GLOBAL),  # File scope toggle: GLOBAL vs CHAT
    visibility: str = Form("department"),  # "all" or "department" - who can see the file
    session_id: Optional[str] = Form(None),  # Required for CHAT scope
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    NEW UNIFIED UPLOAD API (2025) - Advanced RAG Pipeline

    Features:
    - SHA-256 deduplication prevents duplicate files
    - Automatic metadata extraction (no user input required)
    - Multi-format support: PDF, DOCX, XLSX, PPTX, Images, Text
    - Intelligent text chunking optimized for RAG
    - Multilingual embedding generation (German + English optimized)
    - File scope toggle: Company database vs Chat-only
    - OCR support for scanned documents (when available)
    """
    from app.models import ChatSession

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

    # Prepare safe filenames
    original_display_name = Path(file.filename).name if file.filename else "upload"
    original_display_name = original_display_name.replace("\x00", "").strip()
    if not original_display_name:
        original_display_name = "upload"
    safe_original_for_path = sanitize_filename(original_display_name)
    file_id = str(uuid.uuid4())
    file_ext = Path(safe_original_for_path).suffix or Path(original_display_name).suffix
    saved_filename = sanitize_filename(f"{file_id}{file_ext}", fallback_prefix="upload")
    file_path = secure_join(UPLOAD_DIR, saved_filename, fallback_prefix="upload")

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
        # PROCESS WITH ADVANCED DOCUMENT PROCESSOR (2025)
        processing_result = await document_processor.process_document(
            file_path=file_path,
            original_filename=original_display_name,
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

                user_department_value = (
                    getattr(current_user.primary_department, "value", None)
                    if hasattr(current_user.primary_department, "value")
                    else None
                )
                if not user_department_value and current_user.primary_department:
                    user_department_value = str(current_user.primary_department)

                if user_department_value:
                    existing_meta = dict(existing_doc.meta_data or {})
                    raw_allowed = existing_meta.get("allowed_departments")
                    if isinstance(raw_allowed, list):
                        allowed_departments = [str(dep) for dep in raw_allowed if dep]
                    elif raw_allowed:
                        allowed_departments = [str(raw_allowed)]
                    else:
                        allowed_departments = []

                    allowed_upper = {dep.upper() for dep in allowed_departments if isinstance(dep, str)}
                    if "ALL" not in allowed_upper and user_department_value not in allowed_departments:
                        allowed_departments.append(user_department_value)
                        existing_meta["allowed_departments"] = allowed_departments
                        existing_doc.meta_data = existing_meta
                        try:
                            db.add(existing_doc)
                            db.commit()
                            db.refresh(existing_doc)
                        except Exception:
                            db.rollback()
                            logger.warning(
                                "Failed to extend allowed_departments for duplicate document",
                                exc_info=True,
                            )

                return {
                    "duplicate": True,
                    "existing_document_id": str(existing_doc.id),
                    "message": f"File already exists: {existing_doc.filename}",
                    "filename": existing_doc.filename,
                    "original_filename": existing_doc.original_filename,
                    "title": existing_doc.title,
                    "content": existing_doc.content,  # Content is returned so the client can reuse it without reprocessing
                    "content_length": len(existing_doc.content) if existing_doc.content else 0,
                    "mime_type": existing_doc.mime_type,
                    "file_type": existing_doc.file_type,
                    "scope": "GLOBAL",
                    "created_at": existing_doc.created_at.isoformat(),
                    "meta_data": existing_doc.meta_data,
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
                original_filename=original_display_name,
                file_path=str(file_path),
                file_type=processing_result["file_type"],
                file_size=os.path.getsize(file_path),
                mime_type=processing_result["mime_type"],
                file_hash=file_hash,
                title=enhanced_metadata.get("title", original_display_name),
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
                original_filename=original_display_name,
                file_path=str(file_path),
                file_type=processing_result["file_type"],
                file_size=os.path.getsize(file_path),
                mime_type=processing_result["mime_type"],
                file_hash=file_hash,
                title=chat_metadata.get("title", original_display_name),
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


@router.post("/{document_id}/reprocess")
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
