import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatSession, ChatMessage, Document, FileType, User
from app.auth import get_current_user as auth_get_current_user

logger = logging.getLogger(__name__)

# Upload directory configuration
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

router = APIRouter(prefix="/api/v1/chat/sessions", tags=["Chat Sessions"])


# Dependency to get current user (matches main.py pattern)
async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from token."""
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


class PublishSessionRequest(BaseModel):
    title: str
    description: Optional[str] = None


class PublishSessionResponse(BaseModel):
    message: str
    document_id: str


@router.post("/{session_id}/publish", response_model=PublishSessionResponse)
async def publish_session(
    session_id: str,
    request: PublishSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Publish a completed chat session as a new document in the knowledge base.

    This creates a Markdown document containing the full chat conversation
    and adds it to the document library for future RAG retrieval.
    """

    # 1. Verify session exists and belongs to current user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat-Sitzung nicht gefunden"
        )

    # 2. Get all messages from the session
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat-Sitzung enthält keine Nachrichten"
        )

    # 3. Generate Markdown content
    markdown_lines = [
        f"# {request.title}",
        "",
        f"This document was generated from a chat session on {datetime.utcnow().strftime('%Y-%m-%d')}.",
        ""
    ]

    if request.description:
        markdown_lines.extend([
            request.description,
            ""
        ])

    markdown_lines.append("---")
    markdown_lines.append("")

    for message in messages:
        if message.role == "user":
            markdown_lines.extend([
                "### User",
                f"> {message.content}",
                ""
            ])
        elif message.role == "assistant":
            markdown_lines.extend([
                "### Assistant",
                message.content,
                ""
            ])

    markdown_content = "\n".join(markdown_lines)

    # 4. Save file to disk
    new_document_id = uuid.uuid4()
    filename = f"{new_document_id}.md"
    file_path = UPLOAD_DIR / filename

    try:
        file_path.write_text(markdown_content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Speichern der Datei: {str(e)}"
        )

    # 5. Create Document record
    new_document = Document(
        id=new_document_id,
        filename=filename,
        original_filename=f"{request.title}.md",
        file_path=str(file_path),
        file_type=FileType.TEXT,
        mime_type="text/markdown",
        file_size=len(markdown_content.encode("utf-8")),
        title=request.title,
        description=request.description,
        uploaded_by=current_user.id,
        department=current_user.primary_department,
        processed=False
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    # 6. Trigger background processing
    try:
        from app.workers.document_tasks import process_document
        process_document.delay(str(new_document.id))
    except Exception as e:
        # If Celery is not available, log the error but don't fail the request
        # The document is still created and can be processed manually later
        logger.warning(
            f"Failed to trigger background processing for document {new_document.id}: {str(e)}"
        )

    # 7. Return success response
    return PublishSessionResponse(
        message="Chat session published successfully",
        document_id=str(new_document.id)
    )
