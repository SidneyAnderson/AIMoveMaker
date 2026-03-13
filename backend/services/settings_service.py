"""Settings service."""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.setting import Setting


async def list_settings(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> tuple[list[Setting], int]:
    count_result = await db.execute(
        select(func.count()).select_from(Setting).where(Setting.scope == "global")
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Setting)
        .where(Setting.scope == "global")
        .order_by(Setting.key)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def update_setting(
    db: AsyncSession, key: str, value: str, user_id: str
) -> Setting:
    result = await db.execute(
        select(Setting).where(Setting.key == key, Setting.scope == "global")
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    setting.value = value
    setting.updated_by = user_id
    await db.flush()
    return setting
