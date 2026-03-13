"""Integration routers — Civitai, HuggingFace, Vast.ai search/offers."""
from fastapi import APIRouter

from backend.schemas.integrations import (
    CivitaiSearchResponse,
    HuggingFaceSearchResponse,
    VastaiOffersResponse,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/civitai/search", response_model=CivitaiSearchResponse)
async def search_civitai(query: str = "", type: str = "", page: int = 1):
    """Search Civitai for models and LoRAs."""
    return CivitaiSearchResponse(results=[], total=0, page=page)


@router.get("/huggingface/search", response_model=HuggingFaceSearchResponse)
async def search_huggingface(query: str = "", type: str = ""):
    """Search HuggingFace for models."""
    return HuggingFaceSearchResponse(results=[], total=0)


@router.get("/vastai/offers", response_model=VastaiOffersResponse)
async def get_vastai_offers(min_vram_mb: int = 0, max_price_per_hr: float = 10.0):
    """Get available Vast.ai GPU offers."""
    return VastaiOffersResponse(offers=[], total=0)
