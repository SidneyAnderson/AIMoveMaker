"""Tracks router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.timeline import TrackCreate, TrackListResponse, TrackResponse, TrackUpdate
from backend.services.timeline_service import create_track, delete_track, list_tracks, update_track

router = APIRouter(prefix="/projects/{project_id}/tracks", tags=["Tracks"])


@router.get("/", response_model=TrackListResponse)
async def list_tracks_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tracks, total = await list_tracks(db, project_id)
    return TrackListResponse(tracks=tracks, total=total)


@router.post("/", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def create_track_endpoint(
    project_id: str,
    body: TrackCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_track(db, project_id, body.type, body.name)


@router.patch("/{track_id}", response_model=TrackResponse)
async def update_track_endpoint(
    project_id: str,
    track_id: str,
    body: TrackUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_track(db, track_id, body.model_dump(exclude_unset=True))


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track_endpoint(
    project_id: str,
    track_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_track(db, track_id)
    return None
