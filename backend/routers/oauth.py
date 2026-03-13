"""OAuth router — GET /auth/oauth/{provider}/authorize, GET /auth/oauth/{provider}/callback."""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])


@router.get("/{provider}/authorize")
async def oauth_authorize(provider: str):
    """Initiate OAuth2 authorization code flow with PKCE."""
    return RedirectResponse(url="/")


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str = "", state: str = ""):
    """Handle OAuth2 callback from provider."""
    return {"access_token": "stub", "refresh_token": "stub", "token_type": "bearer"}
