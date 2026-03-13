"""Auth service — login, register, token refresh, password management."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from backend.models.user import User
from backend.models.user_invite import UserInvite


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Validate credentials and return user. Raises HTTPException on failure."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    # Check account state
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
            headers={"X-Error-Code": "account_deactivated"},
        )
    if user.approval_state == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval",
            headers={"X-Error-Code": "account_pending_approval"},
        )
    if user.approval_state == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been rejected",
        )
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    return user


def build_token_pair(user: User) -> dict:
    """Create access + refresh token pair for a user."""
    extra = {"role": user.global_role, "fpc": user.force_password_change}
    access = create_access_token(user.id, extra=extra)
    refresh = create_refresh_token(user.id)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    """Validate refresh token and issue new token pair (rotation)."""
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected refresh token",
        )
    user_id = payload.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return build_token_pair(user)


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    invite_token: str | None = None,
) -> User:
    """Register a new user, optionally via invite token."""
    # Validate password strength
    err = validate_password_strength(password)
    if err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate invite token if provided
    if invite_token:
        result = await db.execute(
            select(UserInvite).where(
                UserInvite.token == invite_token,
                UserInvite.used_at.is_(None),
            )
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used invite token",
            )
        if invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite token has expired",
            )

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        global_role="user",
        is_active=False if invite_token else True,
        approval_state="pending" if invite_token else "approved",
        force_password_change=False,
    )
    db.add(user)
    await db.flush()

    # Mark invite as used
    if invite_token:
        invite.used_at = datetime.now(timezone.utc)
        invite.used_by = user.id

    return user


async def change_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    """Change user password. Validates current password and strength."""
    if user.password_hash and not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    err = validate_password_strength(new_password)
    if err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)
    user.password_hash = hash_password(new_password)
    user.force_password_change = False
