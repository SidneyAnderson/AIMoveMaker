"""Keyframes router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.storyboard import (
    KeyframeCreate,
    KeyframeListResponse,
    KeyframeResponse,
    KeyframeUpdate,
)
from backend.services.storyboard_service import (
    create_keyframe,
    delete_keyframe,
    get_keyframe,
    list_keyframes,
    update_keyframe,
)

router = APIRouter(prefix="/projects/{project_id}/keyframes", tags=["Keyframes"])


@router.get("/", response_model=KeyframeListResponse)
async def list_keyframes_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    keyframes, total = await list_keyframes(db, project_id)
    return KeyframeListResponse(keyframes=keyframes, total=total)


@router.post("/", response_model=KeyframeResponse, status_code=status.HTTP_201_CREATED)
async def create_keyframe_endpoint(
    project_id: str,
    body: KeyframeCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_keyframe(db, project_id, current_user.id, body.model_dump())


@router.get("/{keyframe_id}", response_model=KeyframeResponse)
async def get_keyframe_endpoint(
    project_id: str,
    keyframe_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_keyframe(db, keyframe_id)


@router.patch("/{keyframe_id}", response_model=KeyframeResponse)
async def update_keyframe_endpoint(
    project_id: str,
    keyframe_id: str,
    body: KeyframeUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_keyframe(db, keyframe_id, body.model_dump(exclude_unset=True))


@router.delete("/{keyframe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyframe_endpoint(
    project_id: str,
    keyframe_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_keyframe(db, project_id, keyframe_id)
    return None
