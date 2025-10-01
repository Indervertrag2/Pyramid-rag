from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import ChatSession, ChatMessage
from app.api.deps import get_current_user
from app.services.llm_service import LLMService

router = APIRouter(prefix="/chat", tags=["Chat"])


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
    created_at: str
    updated_at: str
    message_count: int


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List user's chat sessions."""

    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()

    session_responses = []
    for session in sessions:
        # Count messages
        msg_result = await db.execute(
            select(ChatMessage.id).where(ChatMessage.session_id == session.id)
        )
        message_count = len(msg_result.all())

        session_responses.append(
            ChatSessionResponse(
                id=str(session.id),
                title=session.title,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                message_count=message_count
            )
        )

    return session_responses


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    title: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new chat session."""

    session = ChatSession(
        user_id=current_user.id,
        title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse(
        id=str(session.id),
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        message_count=0
    )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
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
            use_rag=msg.use_rag or False,
            retrieved_documents=msg.retrieved_documents or [],
            tokens_used=msg.tokens_used,
            processing_time=msg.processing_time,
            created_at=msg.created_at.isoformat()
        )
        for msg in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
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
        use_rag=message_data.use_rag
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
            use_rag=response_data["use_rag"],
            retrieved_documents=response_data["retrieved_documents"],
            tokens_used=response_data["tokens_used"],
            processing_time=response_data["processing_time"]
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


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
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