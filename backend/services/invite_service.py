"""Invite service — send, list, revoke invites."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user_invite import UserInvite


async def send_invite(db: AsyncSession, email: str, admin_id: str) -> UserInvite:
    """Create an invite token for a prospective user. Expires in 7 days."""
    token = secrets.token_hex(32)
    invite = UserInvite(
        email=email,
        token=token,
        created_by=admin_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.flush()
    return invite


async def list_invites(db: AsyncSession, skip: int = 0, limit: int = 100) -> tuple[list[UserInvite], int]:
    count_result = await db.execute(select(func.count()).select_from(UserInvite))
    total = count_result.scalar() or 0
    result = await db.execute(
        select(UserInvite).order_by(UserInvite.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def revoke_invite(db: AsyncSession, invite_id: str) -> None:
    result = await db.execute(select(UserInvite).where(UserInvite.id == invite_id))
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if invite.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite already used")
    await db.delete(invite)
    await db.flush()
