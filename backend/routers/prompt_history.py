"""Prompt history router."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.prompts import PromptHistoryCreate, PromptHistoryListResponse, PromptHistoryResponse
from backend.services.prompt_service import create_history, list_history


router = APIRouter(prefix="/prompt-history", tags=["Prompt History"])


@router.get("/", response_model=PromptHistoryListResponse)
async def list_history_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    history, total = await list_history(db, current_user.id, project_id, skip, limit)
    return PromptHistoryListResponse(items=history, total=total)


@router.post("/", response_model=PromptHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_history_endpoint(
    body: PromptHistoryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_history(db, current_user.id, body.model_dump())
