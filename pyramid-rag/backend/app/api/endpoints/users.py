from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.auth import get_password_hash, validate_password_strength
from app.models import User, Department, AuditLog
from app.api.deps import get_current_superuser, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    primary_department: str
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    primary_department: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    primary_department: str
    is_active: bool
    is_superuser: bool
    created_at: str
    last_login: Optional[str]


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """List all users (admin only)."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            primary_department=user.primary_department,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        for user in users
    ]


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Create a new user (admin only)."""

    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) |
            (User.username == user_data.username)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer mit dieser E-Mail oder diesem Benutzernamen existiert bereits"
        )

    # Validate password
    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        primary_department=user_data.primary_department,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Log user creation
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_created",
        resource_type="user",
        resource_id=user.id,
        details={"created_user_email": user.email}
    )
    db.add(audit_log)
    await db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        primary_department=user.primary_department,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat(),
        last_login=None
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID."""

    # Users can view their own profile, admins can view any
    if not current_user.is_superuser and str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nicht genügend Berechtigungen"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        primary_department=user.primary_department,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Update user (admin only)."""

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden"
        )

    # Update fields
    update_data = {}
    for field, value in user_data.dict(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value

    if update_data:
        await db.execute(
            update(User).where(User.id == user_id).values(**update_data)
        )
        await db.commit()
        await db.refresh(user)

    # Log user update
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_updated",
        resource_type="user",
        resource_id=user.id,
        details={"updated_fields": list(update_data.keys())}
    )
    db.add(audit_log)
    await db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        primary_department=user.primary_department,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Delete user (admin only)."""

    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sie können sich nicht selbst löschen"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden"
        )

    # Log user deletion before deleting
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_deleted",
        resource_type="user",
        resource_id=user.id,
        details={"deleted_user_email": user.email}
    )
    db.add(audit_log)

    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    return {"message": "Benutzer erfolgreich gelöscht"}