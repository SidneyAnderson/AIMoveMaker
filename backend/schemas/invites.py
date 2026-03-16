"""User invite schemas."""
from datetime import datetime

from pydantic import BaseModel, EmailStr


class InviteCreate(BaseModel):
    email: EmailStr


class InviteResponse(BaseModel):
    id: str
    email: str
    token: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    used_by: str | None = None

    model_config = {"from_attributes": True}


class InviteListResponse(BaseModel):
    items: list[InviteResponse]
    total: int
    page: int = 1
    page_size: int = 100
    pages: int = 1
