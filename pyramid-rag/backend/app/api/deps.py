from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.database import get_async_db
# from app.core.config import settings  # Not needed here
from app.auth import decode_token
from app.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültige Authentifizierungsdaten",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inaktiver Benutzer"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nicht genügend Berechtigungen"
        )
    return current_user


def check_department_access(
    user: User,
    department: str,
    allow_superuser: bool = True
) -> bool:
    if allow_superuser and user.is_superuser:
        return True
    if user.primary_department == department:
        return True
    # For now, only check primary department since we removed the many-to-many relationship
    return False


def check_document_access(
    user: User,
    document,
    allow_superuser: bool = True
) -> bool:
    if allow_superuser and user.is_superuser:
        return True

    # Personal documents
    if document.scope == "personal":
        return document.owner_id == user.id

    # Department documents
    if document.scope == "department":
        return check_department_access(user, document.department, allow_superuser=False)

    # Company documents - all authenticated users
    if document.scope == "company":
        return True

    return False