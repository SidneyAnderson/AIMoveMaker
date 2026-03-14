"""Storyboard and keyframe service."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.keyframe import Keyframe
from backend.models.storyboard import Storyboard


async def get_storyboard(db: AsyncSession, project_id: str) -> Storyboard:
    result = await db.execute(
        select(Storyboard).where(Storyboard.project_id == project_id)
    )
    storyboard = result.scalar_one_or_none()
    if storyboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storyboard not found for this project",
        )
    return storyboard


async def reorder_keyframes(
    db: AsyncSession, project_id: str, keyframe_ids: list[str]
) -> Storyboard:
    """Atomically reorder keyframes by assigning new indices."""
    storyboard = await get_storyboard(db, project_id)
    result = await db.execute(
        select(Keyframe).where(Keyframe.storyboard_id == storyboard.id)
    )
    keyframes = {kf.id: kf for kf in result.scalars().all()}

    for idx, kf_id in enumerate(keyframe_ids):
        if kf_id not in keyframes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Keyframe {kf_id} not found in storyboard",
            )
        keyframes[kf_id].index = idx

    storyboard.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return storyboard


# ---------------------------------------------------------------------------
# Keyframes
# ---------------------------------------------------------------------------

async def list_keyframes(
    db: AsyncSession, project_id: str
) -> tuple[list[Keyframe], int]:
    storyboard = await get_storyboard(db, project_id)
    result = await db.execute(
        select(Keyframe)
        .where(Keyframe.storyboard_id == storyboard.id)
        .order_by(Keyframe.index)
    )
    keyframes = list(result.scalars().all())
    return keyframes, len(keyframes)


async def create_keyframe(
    db: AsyncSession, project_id: str, user_id: str, data: dict
) -> Keyframe:
    storyboard = await get_storyboard(db, project_id)

    # Determine index — append to end or insert after
    insert_after = data.pop("insert_after", None)
    data.pop("order_index", None)   # schema alias, not a model column
    data.pop("prompt", None)        # schema alias for positive_prompt
    result = await db.execute(
        select(func.max(Keyframe.index)).where(
            Keyframe.storyboard_id == storyboard.id
        )
    )
    max_index = result.scalar() or -1

    if insert_after:
        # Find the keyframe to insert after
        ref_result = await db.execute(
            select(Keyframe).where(Keyframe.id == insert_after)
        )
        ref_kf = ref_result.scalar_one_or_none()
        if ref_kf is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="insert_after keyframe not found",
            )
        new_index = ref_kf.index + 1
        # Shift subsequent keyframes
        subsequent = await db.execute(
            select(Keyframe).where(
                Keyframe.storyboard_id == storyboard.id,
                Keyframe.index >= new_index,
            )
        )
        for kf in subsequent.scalars().all():
            kf.index += 1
    else:
        new_index = max_index + 1

    keyframe = Keyframe(
        storyboard_id=storyboard.id,
        index=new_index,
        created_by=user_id,
        **data,
    )
    db.add(keyframe)
    storyboard.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return keyframe


async def get_keyframe(db: AsyncSession, keyframe_id: str) -> Keyframe:
    result = await db.execute(select(Keyframe).where(Keyframe.id == keyframe_id))
    keyframe = result.scalar_one_or_none()
    if keyframe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Keyframe not found"
        )
    return keyframe


async def update_keyframe(db: AsyncSession, keyframe_id: str, data: dict) -> Keyframe:
    keyframe = await get_keyframe(db, keyframe_id)
    for key, value in data.items():
        if value is not None and hasattr(keyframe, key):
            setattr(keyframe, key, value)
    await db.flush()
    return keyframe


async def delete_keyframe(db: AsyncSession, project_id: str, keyframe_id: str) -> None:
    keyframe = await get_keyframe(db, keyframe_id)
    storyboard = await get_storyboard(db, project_id)

    deleted_index = keyframe.index
    await db.delete(keyframe)

    # Re-index subsequent keyframes
    result = await db.execute(
        select(Keyframe).where(
            Keyframe.storyboard_id == storyboard.id,
            Keyframe.index > deleted_index,
        )
    )
    for kf in result.scalars().all():
        kf.index -= 1

    storyboard.updated_at = datetime.now(timezone.utc)
    await db.flush()
