"""Asset schemas."""
from datetime import datetime

from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    project_id: str
    job_id: str | None = None
    type: str
    subtype: str
    # NOTE: storage_path intentionally excluded per PRD 13.11
    mime_type: str
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    file_size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    page: int = 1
    page_size: int = 100
    pages: int = 1
