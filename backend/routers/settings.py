"""Settings router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_admin
from backend.models.user import User
from backend.schemas.settings import SettingListResponse, SettingResponse, SettingUpdate
from backend.services.settings_service import list_settings, update_setting

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=SettingListResponse)
async def list_settings_endpoint(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    settings, total = await list_settings(db)
    return SettingListResponse(
        settings=[
            SettingResponse(
                id=s.id, key=s.key,
                value=None if s.is_secret else s.value,
                value_type=s.value_type, scope=s.scope,
                scope_id=s.scope_id, description=s.description,
                is_secret=s.is_secret,
                is_set=bool(s.value) if s.is_secret else False,
                updated_by=s.updated_by, updated_at=s.updated_at,
            )
            for s in settings
        ],
        total=total,
    )


@router.patch("/{key}", response_model=SettingResponse)
async def update_setting_endpoint(
    key: str,
    body: SettingUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    s = await update_setting(db, key, body.value, admin.id)
    return SettingResponse(
        id=s.id, key=s.key,
        value=None if s.is_secret else s.value,
        value_type=s.value_type, scope=s.scope,
        scope_id=s.scope_id, description=s.description,
        is_secret=s.is_secret,
        is_set=bool(s.value) if s.is_secret else False,
        updated_by=s.updated_by, updated_at=s.updated_at,
    )
