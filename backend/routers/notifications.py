"""Notifications router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.common import MessageResponse
from backend.schemas.notifications import NotificationListResponse, NotificationResponse
from backend.services.notification_service import list_notifications, mark_all_read, mark_read

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def list_notifications_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    notifications, total = await list_notifications(db, current_user.id)
    return NotificationListResponse(items=notifications, total=total)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read_endpoint(
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await mark_read(db, notification_id, current_user.id)


@router.patch("/read-all", response_model=MessageResponse)
async def mark_all_read_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count = await mark_all_read(db, current_user.id)
    return MessageResponse(message=f"{count} notifications marked as read")
