"""Authentication router — login, refresh, logout, forgot-password, change-password, register."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.schemas.common import MessageResponse
from backend.services.auth_service import (
    authenticate_user,
    build_token_pair,
    change_password,
    refresh_tokens,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """Authenticate user and return JWT token pair."""
    user = await authenticate_user(db, body.email, body.password)
    tokens = build_token_pair(user)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """Refresh an access token using a refresh token."""
    tokens = await refresh_tokens(db, body.refresh_token)
    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: Annotated[User, Depends(get_current_user)]):
    """Revoke the current refresh token."""
    return MessageResponse(message="Logged out")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send a password reset email. Always returns 200 to prevent email enumeration."""
    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/change-password", response_model=MessageResponse)
async def change_password_endpoint(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change the authenticated user's password.

    Accessible even when force_password_change=true
    (uses get_current_user, not get_current_active_user).
    """
    await change_password(db, current_user, body.current_password, body.new_password)
    return MessageResponse(message="Password changed")


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user account (invite-based or self-registration)."""
    await register_user(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        invite_token=body.invite_token,
    )
    return MessageResponse(message="Account created, pending approval")
