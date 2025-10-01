from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc
from pydantic import BaseModel
import os
from datetime import datetime
from pathlib import Path

from app.database import get_db
from app.models import Document, FileType, Department
from app.api.deps import get_current_user
from app.services.document_processor import DocumentProcessor

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_size: int
    file_type: Optional[str]
    scope: str
    department: Optional[str]
    status: str
    version: int
    created_at: str
    updated_at: str
    owner_id: str


class DocumentUpload(BaseModel):
    title: str
    scope: DocumentScope
    department: Optional[str] = None
    tags: List[str] = []


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    processed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List documents accessible to the user."""

    query = select(Document)

    # Apply access control - user can see their own docs and their department's docs
    if not current_user.is_superuser:
        from sqlalchemy import or_
        query = query.where(
            or_(
                Document.uploaded_by == current_user.id,
                Document.department == current_user.primary_department
            )
        )

    # Apply filters
    if department:
        query = query.where(Document.department.name == department)
    if processed is not None:
        query = query.where(Document.processed == processed)

    query = query.order_by(desc(Document.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    documents = result.scalars().all()

    return [
        DocumentResponse(
            id=str(doc.id),
            title=doc.title or doc.filename,
            filename=doc.filename,
            file_size=doc.file_size,
            file_type=doc.file_type.value if doc.file_type else "unknown",
            scope=doc.meta_data.get("original_scope", "personal") if doc.meta_data else "personal",
            department=doc.department.value if doc.department else "unknown",
            status="published" if doc.processed else ("failed" if doc.processing_error else "processing"),
            version=1,  # Not implemented yet
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
            owner_id=str(doc.uploaded_by)
        )
        for doc in documents
    ]


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    scope: str = Form(...),
    department: Optional[str] = Form(None),
    tags: str = Form(""),
    process: bool = Form(True),  # Whether to save and process in database
    generate_embeddings: bool = Form(True),  # Whether to generate embeddings (only if process=True)
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload a new document with optional processing and embedding generation."""

    temp_path = None
    document = None

    # If not processing (temporary file for chat context only)
    if not process:
        # For temporary files, just return immediately without database storage
        return {
            "message": "Datei für temporären Chat-Kontext angehängt",
            "document_id": f"temp-{file.filename}",
            "status": "temporary",
            "process": False,
            "generate_embeddings": False
        }

    # Validate file size
    max_upload_size = int(os.getenv('MAX_UPLOAD_SIZE', '1073741824'))  # 1GB default
    if file.size and file.size > max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Datei zu groß. Maximum: {max_upload_size} bytes"
        )

    # Set department based on scope
    if scope == "personal":
        doc_department = None
    elif scope == "department":
        doc_department = department or current_user.primary_department
    else:  # company
        doc_department = current_user.primary_department

    # Determine file type
    file_extension = file.filename.split('.')[-1].lower() if file.filename else 'unknown'
    file_type_mapping = {
        'pdf': FileType.PDF,
        'doc': FileType.WORD, 'docx': FileType.WORD,
        'xls': FileType.EXCEL, 'xlsx': FileType.EXCEL,
        'ppt': FileType.POWERPOINT, 'pptx': FileType.POWERPOINT,
        'txt': FileType.TEXT, 'md': FileType.TEXT,
        'jpg': FileType.IMAGE, 'jpeg': FileType.IMAGE, 'png': FileType.IMAGE, 'gif': FileType.IMAGE,
        'dwg': FileType.CAD, 'dxf': FileType.CAD,
        'mp4': FileType.VIDEO, 'avi': FileType.VIDEO,
        'mp3': FileType.AUDIO, 'wav': FileType.AUDIO
    }
    detected_file_type = file_type_mapping.get(file_extension, FileType.OTHER)

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

    # Create document record
    document = Document(
        title=title,
        filename=file.filename,
        original_filename=file.filename,
        file_path="",  # Will be set after saving
        file_type=detected_file_type,
        file_size=file.size or 0,
        mime_type=file.content_type,
        description="",
        department=Department[current_user.primary_department.name],
        uploaded_by=current_user.id,
        meta_data={"tags": tag_list, "original_scope": scope},
        processed=False
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Save file temporarily for processing
    temp_dir = os.getenv('TEMP_DIR', '/tmp/pyramid_rag')
    temp_path = os.path.join(temp_dir, f"{document.id}_{file.filename}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Read file content with error handling for disconnections
        content = await file.read()

        # If connection was aborted, content might be None or incomplete
        if not content:
            # Clean up database entry
            await db.delete(document)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload was incomplete or aborted"
            )

        with open(temp_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        # Clean up on any error during file saving
        if document:
            await db.delete(document)
            await db.commit()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        if "aborted" in str(e).lower() or "disconnect" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload was interrupted"
            )
        raise e

    # Initialize document processor
    processor = DocumentProcessor()

    try:
        # Update file path and status to processing
        await db.execute(
            update(Document)
            .where(Document.id == document.id)
            .values(file_path=temp_path, processed=False)
        )
        await db.commit()

        # Process the document (extract text and metadata)
        from app.services.document_processor import FileScopeEnum

        # Map scope to FileScopeEnum
        file_scope = FileScopeEnum.GLOBAL
        if scope == "personal":
            file_scope = FileScopeEnum.PERSONAL
        elif scope == "department":
            file_scope = FileScopeEnum.DEPARTMENT

        # Process document - returns dict with results
        result = await processor.process_document(
            file_path=Path(temp_path),
            original_filename=file.filename,
            scope=file_scope,
            generate_embeddings=generate_embeddings
        )

        # Extract content and metadata from result
        content = result.get("content", "")
        metadata = result.get("metadata", {})

        # Store whether embeddings were generated
        embeddings_generated = bool(result.get("embeddings")) if generate_embeddings else False

        # Update document with extracted content
        await db.execute(
            update(Document)
            .where(Document.id == document.id)
            .values(
                processed=True,
                content=content,
                meta_data={
                    **document.meta_data,
                    **metadata,
                    "embeddings_generated": embeddings_generated,
                    "chunks_count": len(result.get("chunks", [])),
                    "processing_success": result.get("success", False)
                } if document.meta_data else {
                    **metadata,
                    "embeddings_generated": embeddings_generated,
                    "chunks_count": len(result.get("chunks", [])),
                    "processing_success": result.get("success", False)
                }
            )
        )
        await db.commit()

        # Clean up temp file after successful processing
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as cleanup_error:
            # Log but don't fail on cleanup errors
            import logging
            logging.warning(f"Failed to clean up temp file {temp_path}: {cleanup_error}")

    except Exception as e:
        # Handle processing errors gracefully
        import logging
        logging.error(f"Document processing error for {document.id}: {str(e)}")

        await db.execute(
            update(Document)
            .where(Document.id == document.id)
            .values(
                processed=False,
                processing_error=str(e)
            )
        )
        await db.commit()

        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "message": "Dokument erfolgreich hochgeladen",
        "document_id": str(document.id),
        "status": "processing"
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get document by ID."""

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )

    # Check access - user can see their own docs and their department's docs
    if not current_user.is_superuser:
        if document.uploaded_by != current_user.id and document.department != current_user.primary_department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Zugriff verweigert"
            )

    return DocumentResponse(
        id=str(document.id),
        title=document.title or document.filename,
        filename=document.filename,
        file_size=document.file_size,
        file_type=document.file_type.value if document.file_type else "unknown",
        scope=document.meta_data.get("original_scope", "personal") if document.meta_data else "personal",
        department=document.department.value if document.department else "unknown",
        status="published" if document.processed else ("failed" if document.processing_error else "processing"),
        version=1,  # Not implemented yet
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
        owner_id=str(document.uploaded_by)
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete document."""

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )

    # Check if user can delete (owner or admin)
    if not current_user.is_superuser and document.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur der Eigentümer oder Administrator kann dieses Dokument löschen"
        )

    # Delete file if exists
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)

    # Delete document record
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()

    return {"message": "Dokument erfolgreich gelöscht"}