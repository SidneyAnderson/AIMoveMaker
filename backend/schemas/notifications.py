"""Notification schemas."""
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    project_id: str | None = None
    type: str
    channel: str
    payload: dict | None = None
    sent_at: datetime | None = None
    delivered: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int = 1
    page_size: int = 100
    pages: int = 1
