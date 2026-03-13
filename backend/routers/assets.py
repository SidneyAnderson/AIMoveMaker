"""Assets router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.assets import AssetListResponse, AssetResponse
from backend.services.asset_service import delete_asset, get_asset, get_asset_path, list_assets

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["Assets"])


@router.get("/", response_model=AssetListResponse)
async def list_assets_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    assets, total = await list_assets(db, project_id)
    return AssetListResponse(assets=assets, total=total)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_endpoint(
    project_id: str,
    asset_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_asset(db, asset_id)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_endpoint(
    project_id: str,
    asset_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_asset(db, asset_id)
    return None


@router.get("/{asset_id}/download")
async def download_asset_endpoint(
    project_id: str,
    asset_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    asset = await get_asset(db, asset_id)
    path = await get_asset_path(db, asset_id)
    return FileResponse(path, media_type=asset.mime_type, filename=asset_id)
