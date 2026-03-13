"""Model registry and LoRA registry service."""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.lora_registry import LoRARegistry
from backend.models.model_registry import ModelRegistry


# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------

async def list_models(
    db: AsyncSession,
    type_filter: str | None = None,
    architecture: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[ModelRegistry], int]:
    q = select(ModelRegistry).where(ModelRegistry.is_active == True)
    cq = select(func.count()).select_from(ModelRegistry).where(ModelRegistry.is_active == True)

    if type_filter:
        q = q.where(ModelRegistry.type == type_filter)
        cq = cq.where(ModelRegistry.type == type_filter)
    if architecture:
        q = q.where(ModelRegistry.architecture == architecture)
        cq = cq.where(ModelRegistry.architecture == architecture)

    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(q.order_by(ModelRegistry.added_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def register_model(db: AsyncSession, user_id: str, data: dict) -> ModelRegistry:
    # Check name uniqueness
    existing = await db.execute(
        select(ModelRegistry).where(ModelRegistry.name == data.get("name"))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model with this name already exists",
        )

    # Check sha256_hash deduplication
    sha = data.get("sha256_hash")
    if sha:
        dup = await db.execute(
            select(ModelRegistry).where(ModelRegistry.sha256_hash == sha)
        )
        existing_model = dup.scalar_one_or_none()
        if existing_model:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model with same sha256 already exists: {existing_model.name}",
            )

    model = ModelRegistry(added_by=user_id, **data)
    db.add(model)
    await db.flush()
    return model


async def get_model(db: AsyncSession, model_id: str) -> ModelRegistry:
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == model_id))
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
        )
    return model


async def update_model(db: AsyncSession, model_id: str, data: dict) -> ModelRegistry:
    model = await get_model(db, model_id)
    for key, value in data.items():
        if value is not None and hasattr(model, key):
            setattr(model, key, value)
    await db.flush()
    return model


async def delete_model(db: AsyncSession, model_id: str) -> None:
    model = await get_model(db, model_id)
    model.is_active = False  # Soft delete
    await db.flush()


# ---------------------------------------------------------------------------
# LoRA Registry
# ---------------------------------------------------------------------------

async def list_loras(
    db: AsyncSession,
    architecture: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[LoRARegistry], int]:
    q = select(LoRARegistry).where(LoRARegistry.is_active == True)
    cq = select(func.count()).select_from(LoRARegistry).where(LoRARegistry.is_active == True)

    if architecture:
        q = q.where(LoRARegistry.architecture == architecture)
        cq = cq.where(LoRARegistry.architecture == architecture)

    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(q.order_by(LoRARegistry.added_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def register_lora(db: AsyncSession, user_id: str, data: dict) -> LoRARegistry:
    sha = data.get("sha256_hash")
    if sha:
        dup = await db.execute(
            select(LoRARegistry).where(LoRARegistry.sha256_hash == sha)
        )
        existing = dup.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"LoRA with same sha256 already exists: {existing.name}",
            )

    lora = LoRARegistry(added_by=user_id, **data)
    db.add(lora)
    await db.flush()
    return lora


async def delete_lora(db: AsyncSession, lora_id: str) -> None:
    result = await db.execute(select(LoRARegistry).where(LoRARegistry.id == lora_id))
    lora = result.scalar_one_or_none()
    if lora is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="LoRA not found"
        )
    lora.is_active = False  # Soft delete
    await db.flush()
