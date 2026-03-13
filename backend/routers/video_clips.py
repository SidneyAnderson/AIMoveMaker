"""VideoClips router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.timeline import VideoClipCreate, VideoClipListResponse, VideoClipResponse, VideoClipUpdate
from backend.services.timeline_service import (
    create_video_clip, delete_video_clip, get_video_clip,
    list_video_clips, update_video_clip,
)

router = APIRouter(prefix="/projects/{project_id}/videoclips", tags=["Video Clips"])


@router.get("/", response_model=VideoClipListResponse)
async def list_video_clips_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    clips, total = await list_video_clips(db, project_id)
    return VideoClipListResponse(video_clips=clips, total=total)


@router.post("/", response_model=VideoClipResponse, status_code=status.HTTP_201_CREATED)
async def create_video_clip_endpoint(
    project_id: str,
    body: VideoClipCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_video_clip(db, body.model_dump())


@router.get("/{clip_id}", response_model=VideoClipResponse)
async def get_video_clip_endpoint(
    project_id: str,
    clip_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_video_clip(db, clip_id)


@router.patch("/{clip_id}", response_model=VideoClipResponse)
async def update_video_clip_endpoint(
    project_id: str,
    clip_id: str,
    body: VideoClipUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_video_clip(db, clip_id, body.model_dump(exclude_unset=True))


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_clip_endpoint(
    project_id: str,
    clip_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_video_clip(db, clip_id)
    return None
