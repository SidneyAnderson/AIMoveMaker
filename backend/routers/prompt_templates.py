"""Prompt templates router."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.prompts import (
    PromptTemplateCreate,
    PromptTemplateListResponse,
    PromptTemplateResponse,
)
from backend.services.prompt_service import create_template, list_templates


router = APIRouter(prefix="/prompt-templates", tags=["Prompt Templates"])


@router.get("/", response_model=PromptTemplateListResponse)
async def list_templates_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    templates, total = await list_templates(db, current_user.id, project_id, skip, limit)
    return PromptTemplateListResponse(items=templates, total=total)


@router.post("/", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template_endpoint(
    body: PromptTemplateCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_template(db, current_user.id, body.model_dump())


@router.post("/{template_id}/apply")
async def apply_template_endpoint(
    template_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    keyframe_id: str | None = None,
):
    from backend.services.prompt_service import apply_template
    data = await apply_template(db, template_id, current_user.id)
    return data
