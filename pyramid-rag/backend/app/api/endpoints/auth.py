from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength
)
# from app.core.config import settings
from app.models import User, RefreshToken, AuditLog
from app.api.deps import security, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        # Log failed login attempt
        audit_log = AuditLog(
            action="login_failed",
            resource_type="auth",
            details={"email": request.email},
            created_at=datetime.utcnow()
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige E-Mail oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzerkonto ist deaktiviert"
        )

    # Create tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Store refresh token
    refresh_token_obj = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token_obj)

    # Update last login
    await db.execute(
        update(User).where(User.id == user.id).values(last_login=datetime.utcnow())
    )

    # Log successful login
    audit_log = AuditLog(
        user_id=user.id,
        action="login_success",
        resource_type="auth",
        details={"email": user.email},
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    await db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "primary_department": user.primary_department,
            "is_superuser": user.is_superuser
        }
    )


@router.post("/refresh")
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    # Decode and validate refresh token
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges Refresh-Token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges Refresh-Token"
        )

    # Check if refresh token exists in database
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == request.refresh_token,
            RefreshToken.expires_at > datetime.utcnow()
        )
    )
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh-Token abgelaufen oder ungültig"
        )

    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden"
        )

    # Create new access token
    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    # Remove refresh token from database
    token = credentials.credentials
    payload = decode_token(token)

    if payload:
        user_id = payload.get("sub")
        if user_id:
            # Delete all refresh tokens for this user
            await db.execute(
                RefreshToken.__table__.delete().where(RefreshToken.user_id == user_id)
            )

            # Log logout
            audit_log = AuditLog(
                user_id=user_id,
                action="logout",
                resource_type="auth",
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
            await db.commit()

    return {"message": "Erfolgreich abgemeldet"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aktuelles Passwort ist falsch"
        )

    # Validate new password strength
    is_valid, message = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Update password
    hashed_password = get_password_hash(request.new_password)
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(
            hashed_password=hashed_password,
            updated_at=datetime.utcnow()
        )
    )

    # Log password change
    audit_log = AuditLog(
        user_id=current_user.id,
        action="password_changed",
        resource_type="auth",
        created_at=datetime.utcnow()
    )
    db.add(audit_log)

    # Invalidate all refresh tokens
    await db.execute(
        RefreshToken.__table__.delete().where(RefreshToken.user_id == current_user.id)
    )

    await db.commit()

    return {"message": "Passwort erfolgreich geändert"}


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "primary_department": current_user.primary_department,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }