"""Hardware profile exposure (for UI)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_current_active_user
from backend.hardware_profile import (
    check_vram_sufficient,
    estimate_vram_mb,
    get_hardware_profile,
)
from backend.models.user import User

router = APIRouter(prefix="/hardware", tags=["Hardware"])


@router.get("/", summary="Get current hardware profile and optimization strategy")
async def get_hardware_profile_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    strategy = get_hardware_profile()
    return {
        "gpu_class": strategy.gpu_class.value,
        "device_name": strategy.device_name,
        "compute_capability": strategy.compute_capability,
        "vram_total_mb": strategy.vram_total_mb,
        "vram_free_mb": strategy.vram_free_mb,
        "precision": strategy.precision,
        "use_xformers": strategy.use_xformers,
        "torch_compile": strategy.torch_compile,
        "compile_backend": strategy.compile_backend,
    }


@router.get("/estimate", summary="Estimate VRAM for a job and check sufficiency")
async def estimate_vram_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    model_vram_floor_mb: int = Query(2048, description="Base VRAM floor from model registry"),
    width: int = Query(512, ge=64, le=4096),
    height: int = Query(512, ge=64, le=4096),
    frames: int = Query(1, ge=1, le=300),
    lora_count: int = Query(0, ge=0, le=10),
    precision: str = Query("fp16", pattern="^(fp16|bf16|fp32)$"),
):
    """Lightweight estimator for the UI (re-uses the exact same logic as job creation)."""
    estimated = estimate_vram_mb(
        model_vram_floor_mb=model_vram_floor_mb,
        width=width,
        height=height,
        frames=frames,
        lora_count=lora_count,
        precision=precision,
    )
    sufficient, info = check_vram_sufficient(estimated)

    return {
        "estimated_mb": estimated,
        "is_sufficient": sufficient,
        **info,
        "inputs": {
            "model_vram_floor_mb": model_vram_floor_mb,
            "width": width,
            "height": height,
            "frames": frames,
            "lora_count": lora_count,
            "precision": precision,
        },
    }
