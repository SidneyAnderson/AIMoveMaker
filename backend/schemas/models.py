"""Model and LoRA registry schemas."""
from datetime import datetime

from pydantic import BaseModel


class ModelRegistryCreate(BaseModel):
    name: str
    display_name: str
    type: str  # image, video, audio
    architecture: str
    version: str | None = None
    vram_floor_mb: int
    vram_recommended_mb: int
    supports_cpu_offload: bool = False
    supports_fp8: bool = False
    supports_fp16: bool = True
    min_compute_capability: str | None = None
    param_schema: dict | None = None
    compatible_lora_architectures: list | None = None
    lora_weight_min: float = 0.0
    lora_weight_max: float = 2.0
    max_lora_stack_size: int = 5
    storage_path: str
    source_url: str | None = None
    hf_repo_id: str | None = None
    civitai_id: str | None = None
    file_size_bytes: int | None = None
    sha256_hash: str | None = None


class ModelRegistryUpdate(BaseModel):
    display_name: str | None = None
    version: str | None = None
    vram_floor_mb: int | None = None
    vram_recommended_mb: int | None = None
    supports_cpu_offload: bool | None = None
    supports_fp8: bool | None = None
    supports_fp16: bool | None = None
    min_compute_capability: str | None = None
    param_schema: dict | None = None
    compatible_lora_architectures: list | None = None
    lora_weight_min: float | None = None
    lora_weight_max: float | None = None
    max_lora_stack_size: int | None = None
    is_active: bool | None = None


class ModelRegistryResponse(BaseModel):
    id: str
    name: str
    display_name: str
    type: str
    architecture: str
    version: str | None = None
    vram_floor_mb: int
    vram_recommended_mb: int
    supports_cpu_offload: bool
    supports_fp8: bool
    supports_fp16: bool
    min_compute_capability: str | None = None
    param_schema: dict | None = None
    compatible_lora_architectures: list | None = None
    lora_weight_min: float
    lora_weight_max: float
    max_lora_stack_size: int
    storage_path: str
    source_url: str | None = None
    hf_repo_id: str | None = None
    civitai_id: str | None = None
    file_size_bytes: int | None = None
    sha256_hash: str | None = None
    added_by: str
    added_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ModelRegistryListResponse(BaseModel):
    models: list[ModelRegistryResponse]
    total: int


# --- LoRA Registry ---

class LoRARegistryCreate(BaseModel):
    name: str
    display_name: str
    architecture: str
    storage_path: str
    source_url: str | None = None
    hf_repo_id: str | None = None
    civitai_id: str | None = None
    trigger_words: list | None = None
    nsfw_flag: bool = False
    weight_default: float = 1.0
    file_size_bytes: int | None = None
    sha256_hash: str | None = None


class LoRARegistryResponse(BaseModel):
    id: str
    name: str
    display_name: str
    architecture: str
    storage_path: str
    source_url: str | None = None
    hf_repo_id: str | None = None
    civitai_id: str | None = None
    trigger_words: list | None = None
    nsfw_flag: bool
    weight_default: float
    file_size_bytes: int | None = None
    sha256_hash: str | None = None
    added_by: str
    added_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class LoRARegistryListResponse(BaseModel):
    loras: list[LoRARegistryResponse]
    total: int
