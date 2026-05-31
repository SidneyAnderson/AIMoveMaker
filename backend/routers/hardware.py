"""Hardware profile exposure (for UI)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.dependencies import get_current_active_user
from backend.hardware_profile import get_hardware_profile
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
