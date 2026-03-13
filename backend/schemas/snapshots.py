"""Snapshot schemas."""
from datetime import datetime

from pydantic import BaseModel


class SnapshotCreate(BaseModel):
    type: str = "manual"  # manual or checkpoint
    label: str | None = None


class SnapshotResponse(BaseModel):
    id: str
    project_id: str
    type: str
    label: str | None = None
    storage_path: str
    size_bytes: int
    created_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotResponse]
    total: int
