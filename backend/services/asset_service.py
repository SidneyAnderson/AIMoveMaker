"""Asset service — list, get, delete, download."""
import os

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset


async def list_assets(
    db: AsyncSession, project_id: str, skip: int = 0, limit: int = 100
) -> tuple[list[Asset], int]:
    count_result = await db.execute(
        select(func.count())
        .select_from(Asset)
        .where(Asset.project_id == project_id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Asset)
        .where(Asset.project_id == project_id)
        .order_by(Asset.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_asset(db: AsyncSession, asset_id: str) -> Asset:
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return asset


async def delete_asset(db: AsyncSession, asset_id: str) -> None:
    asset = await get_asset(db, asset_id)
    # Optionally remove file from disk
    if asset.storage_path and os.path.exists(asset.storage_path):
        try:
            os.remove(asset.storage_path)
        except OSError:
            pass  # Log but don't fail
    await db.delete(asset)
    await db.flush()


async def get_asset_path(db: AsyncSession, asset_id: str) -> str:
    """Get the file path for download. Validates path safety."""
    asset = await get_asset(db, asset_id)
    if not asset.storage_path or not os.path.exists(asset.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found on disk",
        )
    # Path traversal prevention
    real_path = os.path.realpath(asset.storage_path)
    if not (real_path.startswith("/opt/aimoviemaker/") or "/AIMoveMaker/" in real_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid asset path",
        )
    return real_path
