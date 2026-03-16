"""AudioClips router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.timeline import AudioClipCreate, AudioClipListResponse, AudioClipResponse, AudioClipUpdate
from backend.services.timeline_service import (
    create_audio_clip, delete_audio_clip, get_audio_clip,
    list_audio_clips, update_audio_clip,
)

router = APIRouter(prefix="/projects/{project_id}/audioclips", tags=["Audio Clips"])


@router.get("/", response_model=AudioClipListResponse)
async def list_audio_clips_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    clips, total = await list_audio_clips(db, project_id)
    return AudioClipListResponse(items=clips, total=total)


@router.post("/", response_model=AudioClipResponse, status_code=status.HTTP_201_CREATED)
async def create_audio_clip_endpoint(
    project_id: str,
    body: AudioClipCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_audio_clip(db, body.model_dump())


@router.get("/{clip_id}", response_model=AudioClipResponse)
async def get_audio_clip_endpoint(
    project_id: str,
    clip_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_audio_clip(db, clip_id)


@router.patch("/{clip_id}", response_model=AudioClipResponse)
async def update_audio_clip_endpoint(
    project_id: str,
    clip_id: str,
    body: AudioClipUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_audio_clip(db, clip_id, body.model_dump(exclude_unset=True))


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_clip_endpoint(
    project_id: str,
    clip_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_audio_clip(db, clip_id)
    return None
