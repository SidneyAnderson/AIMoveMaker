"""Notification service — list, mark read."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.notification import Notification


async def list_notifications(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 50
) -> tuple[list[Notification], int]:
    count_result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def mark_read(db: AsyncSession, notification_id: str, user_id: str) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notification.read_at = datetime.now(timezone.utc)
    await db.flush()
    return notification


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    """Mark all unread notifications as read. Returns count updated."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    count = 0
    now = datetime.now(timezone.utc)
    for notification in result.scalars().all():
        notification.read_at = now
        count += 1
    await db.flush()
    return count


async def create_notification(
    db: AsyncSession,
    user_id: str,
    notification_type: str,
    channel: str = "in_app",
    project_id: str | None = None,
    payload: dict | None = None,
) -> Notification:
    """Create and persist a notification."""
    notification = Notification(
        user_id=user_id,
        project_id=project_id,
        type=notification_type,
        channel=channel,
        payload=payload or {},
        sent_at=datetime.now(timezone.utc),
        delivered=True,
    )
    db.add(notification)
    await db.flush()
    return notification
