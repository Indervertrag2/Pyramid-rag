from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_async_db
from app.models import ChatSession, ChatMessage, ChatType
from app.api.deps import get_current_user
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


class ChatMessageCreate(BaseModel):
    content: str
    use_rag: bool = True
    search_mode: str = "hybrid"


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    use_rag: bool
    retrieved_documents: List[dict]
    tokens_used: Optional[int]
    processing_time: Optional[float]
    created_at: str


class ChatSessionResponse(BaseModel):
    id: str
    title: Optional[str]
    folder_path: Optional[str]
    chat_type: str
    expires_at: Optional[str]
    created_at: str
    updated_at: str
    message_count: int


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    folder_path: Optional[str] = None
    is_temporary: bool = False


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    folder_path: Optional[str] = None


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """List user's chat sessions."""

    stmt = (
        select(
            ChatSession,
            func.count(ChatMessage.id).label("message_count")
        )
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.user_id == current_user.id)
        .group_by(ChatSession.id)
        .order_by(desc(ChatSession.updated_at))
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    session_responses = []
    for session, message_count in rows:
        session_responses.append(
            ChatSessionResponse(
                id=str(session.id),
                title=session.title,
                folder_path=session.folder_path,
                chat_type=session.chat_type.value if session.chat_type else "NORMAL",
                expires_at=session.expires_at.isoformat() if session.expires_at else None,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                message_count=message_count or 0
            )
        )

    return session_responses


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Create a new chat session."""

    chat_type = ChatType.TEMPORARY if session_data.is_temporary else ChatType.NORMAL
    expires_at = None
    if session_data.is_temporary:
        expires_at = datetime.utcnow() + timedelta(days=30)

    session = ChatSession(
        user_id=current_user.id,
        title=session_data.title or ("Temporarer Chat" if session_data.is_temporary else "Neuer Chat"),
        folder_path=session_data.folder_path,
        chat_type=chat_type,
        expires_at=expires_at
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse(
        id=str(session.id),
        title=session.title,
        folder_path=session.folder_path,
        chat_type=session.chat_type.value,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        message_count=0
    )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Get messages for a chat session."""

    # Verify session belongs to user
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat-Sitzung nicht gefunden"
        )

    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        ChatMessageResponse(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            use_rag=(msg.meta_data or {}).get('use_rag', False),
            retrieved_documents=(msg.meta_data or {}).get('retrieved_documents', []),
            tokens_used=(msg.meta_data or {}).get('tokens_used'),
            processing_time=(msg.meta_data or {}).get('processing_time'),
            created_at=msg.created_at.isoformat()
        )
        for msg in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Send a message in a chat session."""

    # Verify session belongs to user
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat-Sitzung nicht gefunden"
        )

    # Save user message
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=message_data.content,
        meta_data={'use_rag': message_data.use_rag}
    )
    db.add(user_message)
    await db.commit()

    # Generate AI response
    llm_service = LLMService()
    try:
        response_data = await llm_service.generate_rag_response(
            db=db,
            user=current_user,
            query=message_data.content,
            use_rag=message_data.use_rag,
            search_mode=message_data.search_mode
        )

        # Save AI response
        ai_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_data["response"],
            meta_data={
                'use_rag': response_data["use_rag"],
                'retrieved_documents': response_data["retrieved_documents"],
                'tokens_used': response_data["tokens_used"],
                'processing_time': response_data["processing_time"]
            }
        )
        db.add(ai_message)

        # Update session timestamp
        await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(ai_message)

        return ChatMessageResponse(
            id=str(ai_message.id),
            role=ai_message.role,
            content=ai_message.content,
            use_rag=ai_message.use_rag,
            retrieved_documents=ai_message.retrieved_documents or [],
            tokens_used=ai_message.tokens_used,
            processing_time=ai_message.processing_time,
            created_at=ai_message.created_at.isoformat()
        )

    except Exception as e:
        # Save error message
        error_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=f"Entschuldigung, es ist ein Fehler aufgetreten: {str(e)}",
            use_rag=False
        )
        db.add(error_message)
        await db.commit()
        await db.refresh(error_message)

        return ChatMessageResponse(
            id=str(error_message.id),
            role=error_message.role,
            content=error_message.content,
            use_rag=False,
            retrieved_documents=[],
            tokens_used=0,
            processing_time=0,
            created_at=error_message.created_at.isoformat()
        )


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Update a chat session (title, folder)."""

    # Verify session belongs to user
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat-Sitzung nicht gefunden"
        )

    # Update fields
    if session_data.title is not None:
        session.title = session_data.title
    if session_data.folder_path is not None:
        session.folder_path = session_data.folder_path if session_data.folder_path else None

    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    # Get message count
    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    )
    message_count = count_result.scalar() or 0

    return ChatSessionResponse(
        id=str(session.id),
        title=session.title,
        folder_path=session.folder_path,
        chat_type=session.chat_type.value,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        message_count=message_count
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Delete a chat session."""

    # Verify session belongs to user
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat-Sitzung nicht gefunden"
        )

    # Delete session (messages will be cascade deleted)
    await db.delete(session)
    await db.commit()

    return {"message": "Chat-Sitzung erfolgreich gelöscht"}