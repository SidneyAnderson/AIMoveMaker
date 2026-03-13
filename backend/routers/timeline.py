"""Timeline router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.timeline import TimelineResponse, TimelineUpdate
from backend.services.timeline_service import get_timeline, update_timeline

router = APIRouter(prefix="/projects/{project_id}/timeline", tags=["Timeline"])


@router.get("/", response_model=TimelineResponse)
async def get_timeline_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_timeline(db, project_id)


@router.patch("/", response_model=TimelineResponse)
async def update_timeline_endpoint(
    project_id: str,
    body: TimelineUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_timeline(db, project_id, body.model_dump(exclude_unset=True))
