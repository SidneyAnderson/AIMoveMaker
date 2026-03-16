"""Settings schemas."""
from datetime import datetime

from pydantic import BaseModel


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    id: str
    key: str
    value: str | None = None  # None if is_secret
    value_type: str
    scope: str
    scope_id: str | None = None
    description: str | None = None
    is_secret: bool
    is_set: bool = False  # True if secret has a non-empty value
    updated_by: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingListResponse(BaseModel):
    items: list[SettingResponse]
    total: int
    page: int = 1
    page_size: int = 100
    pages: int = 1
