"""Model Registry router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user, require_admin
from backend.models.user import User
from backend.schemas.models import (
    ModelRegistryCreate, ModelRegistryListResponse,
    ModelRegistryResponse, ModelRegistryUpdate,
)
from backend.services.registry_service import delete_model, list_models, register_model, update_model

router = APIRouter(prefix="/models", tags=["Model Registry"])


@router.get("/", response_model=ModelRegistryListResponse)
async def list_models_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    type_filter: str | None = None,
    architecture: str | None = None,
):
    models, total = await list_models(db, type_filter=type_filter, architecture=architecture)
    return ModelRegistryListResponse(items=models, total=total)


@router.post("/", response_model=ModelRegistryResponse, status_code=status.HTTP_201_CREATED)
async def register_model_endpoint(
    body: ModelRegistryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await register_model(db, current_user.id, body.model_dump())


@router.patch("/{model_id}", response_model=ModelRegistryResponse)
async def update_model_endpoint(
    model_id: str,
    body: ModelRegistryUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_model(db, model_id, body.model_dump(exclude_unset=True))


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_endpoint(
    model_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_model(db, model_id)
    return None
