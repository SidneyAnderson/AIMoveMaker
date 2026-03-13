"""Integration schemas for Civitai, HuggingFace, Vast.ai."""
from pydantic import BaseModel


class CivitaiSearchResult(BaseModel):
    id: str
    name: str
    type: str
    nsfw: bool
    download_url: str | None = None
    description: str | None = None
    tags: list[str] = []


class CivitaiSearchResponse(BaseModel):
    results: list[CivitaiSearchResult]
    total: int
    page: int


class HuggingFaceSearchResult(BaseModel):
    repo_id: str
    model_name: str
    downloads: int
    likes: int
    tags: list[str] = []


class HuggingFaceSearchResponse(BaseModel):
    results: list[HuggingFaceSearchResult]
    total: int


class VastaiOffer(BaseModel):
    instance_id: str
    gpu_name: str
    gpu_ram_mb: int
    num_gpus: int
    cuda_version: str
    price_per_hr_usd: float
    reliability: float


class VastaiOffersResponse(BaseModel):
    offers: list[VastaiOffer]
    total: int
