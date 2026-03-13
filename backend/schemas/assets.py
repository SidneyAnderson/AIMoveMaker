"""Asset schemas."""
from datetime import datetime

from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    project_id: str
    job_id: str | None = None
    type: str
    subtype: str
    storage_path: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    file_size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    total: int
