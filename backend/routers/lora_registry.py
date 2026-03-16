"""LoRA Registry router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user, require_admin
from backend.models.user import User
from backend.schemas.models import LoRARegistryCreate, LoRARegistryListResponse, LoRARegistryResponse
from backend.services.registry_service import delete_lora, list_loras, register_lora

router = APIRouter(prefix="/loras", tags=["LoRA Registry"])


@router.get("/", response_model=LoRARegistryListResponse)
async def list_loras_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    architecture: str | None = None,
):
    loras, total = await list_loras(db, architecture=architecture)
    return LoRARegistryListResponse(items=loras, total=total)


@router.post("/", response_model=LoRARegistryResponse, status_code=status.HTTP_201_CREATED)
async def register_lora_endpoint(
    body: LoRARegistryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await register_lora(db, current_user.id, body.model_dump())


@router.delete("/{lora_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lora_endpoint(
    lora_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_lora(db, lora_id)
    return None
