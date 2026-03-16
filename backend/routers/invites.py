"""User invites router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_admin
from backend.models.user import User
from backend.schemas.invites import InviteCreate, InviteListResponse, InviteResponse
from backend.services.invite_service import list_invites, revoke_invite, send_invite

router = APIRouter(prefix="/invites", tags=["User Invites"])


@router.post("/", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def send_invite_endpoint(
    body: InviteCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin sends an invite to a prospective user."""
    invite = await send_invite(db, email=body.email, admin_id=admin.id)
    return invite


@router.get("/", response_model=InviteListResponse)
async def list_invites_endpoint(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin lists all invites."""
    invites, total = await list_invites(db)
    return InviteListResponse(items=invites, total=total)


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite_endpoint(
    invite_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin revokes an invite."""
    await revoke_invite(db, invite_id)
    return None
