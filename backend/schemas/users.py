"""User schemas."""
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    global_role: str = "user"


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    global_role: str | None = None
    notify_settings: dict | None = None
    auto_save_interval_s: int | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    global_role: str
    is_active: bool
    notify_settings: dict | None = None
    auto_save_interval_s: int
    approval_state: str
    force_password_change: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int = 1
    page_size: int = 100
    pages: int = 1
