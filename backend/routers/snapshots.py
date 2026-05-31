"""Snapshots router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.common import MessageResponse
from backend.schemas.snapshots import SnapshotCreate, SnapshotListResponse, SnapshotResponse
from backend.services.snapshot_service import create_snapshot, list_snapshots, restore_snapshot

router = APIRouter(prefix="/projects/{project_id}/snapshots", tags=["Snapshots"])


@router.get("/", response_model=SnapshotListResponse)
async def list_snapshots_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tier: str | None = None,
):
    snapshots, total = await list_snapshots(db, project_id, tier=tier)
    return SnapshotListResponse(items=snapshots, total=total)


@router.post("/", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot_endpoint(
    project_id: str,
    body: SnapshotCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_snapshot(db, project_id, current_user.id, body.type, body.tier, body.label)


@router.post("/{snapshot_id}/restore", response_model=MessageResponse)
async def restore_snapshot_endpoint(
    project_id: str,
    snapshot_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await restore_snapshot(db, snapshot_id)
    return MessageResponse(message="Snapshot restored")
