"""Storyboard router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.storyboard import StoryboardReorderRequest, StoryboardResponse
from backend.services.storyboard_service import get_storyboard, reorder_keyframes

router = APIRouter(prefix="/projects/{project_id}/storyboard", tags=["Storyboard"])


@router.get("/", response_model=StoryboardResponse)
async def get_storyboard_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_storyboard(db, project_id)


@router.patch("/", response_model=StoryboardResponse)
async def reorder_storyboard_endpoint(
    project_id: str,
    body: StoryboardReorderRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await reorder_keyframes(db, project_id, body.keyframe_ids)
