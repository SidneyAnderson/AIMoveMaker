"""Users router — CRUD with auth dependencies."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user, require_admin
from backend.models.user import User
from backend.schemas.users import UserCreate, UserListResponse, UserResponse, UserUpdate
from backend.services.user_service import (
    create_user_by_admin,
    deactivate_user,
    get_user_by_id,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    """Get the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update the authenticated user's profile (non-admin fields only)."""
    safe_data = body.model_dump(exclude_unset=True, exclude={"is_active", "global_role"})
    updated = await update_user(db, current_user, safe_data)
    return updated


@router.get("/", response_model=UserListResponse)
async def list_all_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """Admin: list all users."""
    users, total = await list_users(db, skip=skip, limit=limit)
    return UserListResponse(items=users, total=total)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    body: UserCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: create a new user."""
    user = await create_user_by_admin(
        db,
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        global_role=body.global_role,
    )
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: str,
    body: UserUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: update a user (including role and active status)."""
    user = await get_user_by_id(db, user_id)
    updated = await update_user(db, user, body.model_dump(exclude_unset=True))
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: deactivate a user."""
    user = await get_user_by_id(db, user_id)
    await deactivate_user(db, user)
    return None
