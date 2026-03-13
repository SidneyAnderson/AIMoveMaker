"""User service — CRUD, admin creation, approval."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import hash_password, validate_password_strength
from backend.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def list_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar() or 0
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def create_user_by_admin(
    db: AsyncSession,
    email: str,
    full_name: str,
    password: str,
    global_role: str = "user",
) -> User:
    """Admin creates a user — immediately active, force_password_change=true."""
    err = validate_password_strength(password)
    if err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        global_role=global_role,
        is_active=True,
        approval_state="approved",
        force_password_change=True,
    )
    db.add(user)
    await db.flush()
    return user


async def update_user(db: AsyncSession, user: User, data: dict) -> User:
    """Update user fields. Handles admin-specific fields like is_active and global_role."""
    for key, value in data.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    await db.flush()
    return user


async def deactivate_user(db: AsyncSession, user: User) -> None:
    """Deactivate a user. Admin accounts must be demoted first."""
    if user.global_role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate admin accounts. Demote to user first.",
        )
    user.is_active = False
    await db.flush()
