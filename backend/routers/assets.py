"""Assets router with auth — list, get, upload, download, delete."""
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.asset import Asset
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
    return AssetListResponse(items=assets, total=total)


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Upload a file as a project asset (image, audio, video)."""
    settings = get_settings()
    asset_id = str(uuid.uuid4())

    # Determine asset type from content type
    content_type = file.content_type or "application/octet-stream"
    if content_type.startswith("image/"):
        asset_type = "image"
    elif content_type.startswith("audio/"):
        asset_type = "audio"
    elif content_type.startswith("video/"):
        asset_type = "video"
    else:
        asset_type = "other"

    # Save file
    asset_dir = os.path.join(settings.STORAGE_BASE_PATH, "assets", project_id)
    os.makedirs(asset_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    file_path = os.path.join(asset_dir, f"{asset_id}{ext}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Determine subtype from asset type
    subtype_map = {
        "image": "still",
        "audio": "music",
        "video": "clip",
        "other": "export",
    }

    # Create asset record (field names match Asset model exactly)
    asset = Asset(
        id=asset_id,
        project_id=project_id,
        type=asset_type,
        subtype=subtype_map.get(asset_type, "export"),
        storage_path=file_path,
        file_size_bytes=len(content),
        mime_type=content_type,
    )
    db.add(asset)
    await db.flush()

    return asset


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
