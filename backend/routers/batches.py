"""Batches router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.jobs import BatchCreate, BatchListResponse, BatchResponse
from backend.services.job_service import create_batch, get_batch, list_batches

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.get("/", response_model=BatchListResponse)
async def list_batches_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = None,
):
    batches, total = await list_batches(db, project_id=project_id)
    return BatchListResponse(batches=batches, total=total)


@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_endpoint(
    body: BatchCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_batch(db, current_user.id, body.project_id, body.name, body.job_ids)


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch_endpoint(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_batch(db, batch_id)
