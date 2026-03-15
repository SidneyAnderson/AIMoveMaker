"""Hardware Profile Service — GPU detection and optimization strategy.

Runs at:
  (1) server startup
  (2) before Vast.ai instance provisioning

Detects GPU class and determines active optimization strategy.
Admin MAY override via gpu_optimization_override key in Setting table.
"""
import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

from loguru import logger


class GPUClass(str, Enum):
    RTX_5090 = "rtx5090"          # sm_120 (Blackwell)
    DATACENTER = "datacenter"      # A100/H100, VRAM >= 40GB, sm >= 8.0
    PROSUMER = "prosumer"          # A6000/RTX 3090, VRAM 24-40GB, sm < 8.0
    UNKNOWN = "unknown"            # Fallback


@dataclass
class OptimizationStrategy:
    """Optimization strategy determined by GPU class."""
    gpu_class: GPUClass
    precision: str                 # fp16, bf16
    torch_compile: bool            # Whether to use torch.compile
    compile_backend: str           # eager, inductor
    use_xformers: bool
    use_flash_attn: bool
    device_name: str = "unknown"
    compute_capability: tuple[int, int] = (0, 0)
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    extra: dict = field(default_factory=dict)


def detect_gpu() -> dict:
    """Detect GPU hardware. Returns dict with device info."""
    info = {
        "has_cuda": False,
        "device_name": "cpu",
        "compute_capability": (0, 0),
        "vram_total_mb": 0,
        "vram_free_mb": 0,
        "device_count": 0,
    }
    try:
        import torch
        if torch.cuda.is_available():
            info["has_cuda"] = True
            info["device_count"] = torch.cuda.device_count()
            info["device_name"] = torch.cuda.get_device_name(0)
            info["compute_capability"] = torch.cuda.get_device_capability(0)
            props = torch.cuda.get_device_properties(0)
            # total_memory (PyTorch 2.1+) or total_mem (older)
            total = getattr(props, "total_memory", None) or getattr(props, "total_mem", 0)
            info["vram_total_mb"] = total // (1024 * 1024)
            mem_free = torch.cuda.mem_get_info(0)
            info["vram_free_mb"] = mem_free[0] // (1024 * 1024)
    except Exception as e:
        logger.warning(f"GPU detection failed: {e}")
    return info


def classify_gpu(gpu_info: dict) -> GPUClass:
    """Classify GPU into one of the known classes."""
    if not gpu_info.get("has_cuda"):
        return GPUClass.UNKNOWN

    cc = gpu_info.get("compute_capability", (0, 0))
    vram = gpu_info.get("vram_total_mb", 0)

    # RTX 5090 — sm_120 (Blackwell)
    if cc == (12, 0):
        return GPUClass.RTX_5090

    # Datacenter — A100/H100, VRAM >= 40GB, sm >= 8.0
    if vram >= 40960 and cc[0] >= 8:
        return GPUClass.DATACENTER

    # Prosumer — A6000/RTX 3090 class, 24-40GB, sm < 8.0
    if 24576 <= vram < 40960:
        return GPUClass.PROSUMER

    return GPUClass.UNKNOWN


def build_strategy(gpu_class: GPUClass, gpu_info: dict) -> OptimizationStrategy:
    """Build optimization strategy for the detected GPU class.

    Per PRD Table 11:
    - RTX 5090: fp16, torch.compile eager, xformers conditional, flash-attn if available
    - A100/H100: bf16, torch.compile inductor, flash-attn 2, no xformers
    - A6000/RTX 3090: fp16, torch.compile eager, xformers
    - Unknown/fallback: fp16, no torch.compile, standard attention
    """
    strategies = {
        GPUClass.RTX_5090: OptimizationStrategy(
            gpu_class=GPUClass.RTX_5090,
            precision="fp16",
            torch_compile=True,
            compile_backend="eager",  # inductor unstable on sm_120
            use_xformers=_check_xformers(),
            use_flash_attn=_check_flash_attn(),
        ),
        GPUClass.DATACENTER: OptimizationStrategy(
            gpu_class=GPUClass.DATACENTER,
            precision="bf16",
            torch_compile=True,
            compile_backend="inductor",
            use_xformers=False,
            use_flash_attn=True,
        ),
        GPUClass.PROSUMER: OptimizationStrategy(
            gpu_class=GPUClass.PROSUMER,
            precision="fp16",
            torch_compile=True,
            compile_backend="eager",
            use_xformers=_check_xformers(),
            use_flash_attn=False,
        ),
        GPUClass.UNKNOWN: OptimizationStrategy(
            gpu_class=GPUClass.UNKNOWN,
            precision="fp16",
            torch_compile=False,
            compile_backend="eager",
            use_xformers=False,
            use_flash_attn=False,
        ),
    }
    strategy = strategies[gpu_class]
    strategy.device_name = gpu_info.get("device_name", "unknown")
    strategy.compute_capability = gpu_info.get("compute_capability", (0, 0))
    strategy.vram_total_mb = gpu_info.get("vram_total_mb", 0)
    strategy.vram_free_mb = gpu_info.get("vram_free_mb", 0)
    return strategy


def _check_xformers() -> bool:
    """Check if xformers is available.

    PRD Section 10.1 Open Item 4: xformers sm_120 (Blackwell) support status.
    RESOLVED: Conditional load is implemented here — xformers is used only if
    importable. If xformers does not support sm_120 at runtime, import will fail
    and we fall back to PyTorch SDPA (Scaled Dot-Product Attention) which is
    always available in PyTorch 2.0+. The RTX_5090 strategy sets
    use_xformers=_check_xformers() so it's automatically conditional.
    """
    try:
        import xformers  # noqa: F401
        return True
    except ImportError:
        return False


def _check_flash_attn() -> bool:
    """Check if flash_attn is available."""
    try:
        import flash_attn  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_cached_strategy: OptimizationStrategy | None = None


def get_hardware_profile(override: str | None = None) -> OptimizationStrategy:
    """Get the active optimization strategy.

    Args:
        override: Admin override string from Setting table
                  (gpu_optimization_override). E.g. "rtx5090", "datacenter".

    Returns:
        OptimizationStrategy for the active GPU.
    """
    global _cached_strategy

    if _cached_strategy is not None and override is None:
        return _cached_strategy

    gpu_info = detect_gpu()

    if override:
        try:
            gpu_class = GPUClass(override)
            logger.info(
                f"Using admin GPU override: {override}",
                extra={"override": override},
            )
        except ValueError:
            logger.warning(f"Invalid GPU override '{override}', using detection")
            gpu_class = classify_gpu(gpu_info)
    else:
        gpu_class = classify_gpu(gpu_info)

    strategy = build_strategy(gpu_class, gpu_info)

    logger.info(
        f"Hardware Profile: {strategy.gpu_class.value} | "
        f"Device: {strategy.device_name} | "
        f"VRAM: {strategy.vram_total_mb}MB | "
        f"Precision: {strategy.precision} | "
        f"Compile: {strategy.torch_compile} ({strategy.compile_backend}) | "
        f"xformers: {strategy.use_xformers} | "
        f"flash-attn: {strategy.use_flash_attn}",
    )

    if override is None:
        _cached_strategy = strategy
    return strategy


def get_vram_info() -> dict:
    """Get current VRAM usage info for the profiler."""
    try:
        import torch
        if torch.cuda.is_available():
            mem_free, mem_total = torch.cuda.mem_get_info(0)
            return {
                "total_mb": mem_total // (1024 * 1024),
                "free_mb": mem_free // (1024 * 1024),
                "used_mb": (mem_total - mem_free) // (1024 * 1024),
            }
    except Exception:
        pass
    return {"total_mb": 0, "free_mb": 0, "used_mb": 0}


def estimate_vram_mb(
    model_vram_floor_mb: int,
    width: int = 512,
    height: int = 512,
    frames: int = 1,
    lora_count: int = 0,
    precision: str = "fp16",
) -> int:
    """Estimate VRAM requirement for a generation job.

    Based on model vram_floor_mb + resolution scaling + frame count + LoRAs.
    """
    base = model_vram_floor_mb

    # Resolution scaling factor (relative to 512x512)
    pixel_ratio = (width * height) / (512 * 512)
    resolution_factor = max(1.0, pixel_ratio * 0.5 + 0.5)

    # Frame count factor for video
    frame_factor = 1.0
    if frames > 1:
        frame_factor = 1.0 + (frames - 1) * 0.05  # ~5% per extra frame

    # LoRA overhead: ~200MB per LoRA
    lora_overhead = lora_count * 200

    # Precision scaling
    precision_factor = 1.0
    if precision == "fp32":
        precision_factor = 2.0
    elif precision == "bf16":
        precision_factor = 1.0

    estimated = int(base * resolution_factor * frame_factor * precision_factor) + lora_overhead
    return estimated


def check_vram_sufficient(
    estimated_mb: int,
    safety_margin_pct: float = 0.10,
) -> tuple[bool, dict]:
    """Check if local VRAM is sufficient for a job.

    Returns (is_sufficient, info_dict).
    """
    vram = get_vram_info()
    available = vram["free_mb"]
    margin = int(vram["total_mb"] * safety_margin_pct)
    effective_available = max(0, available - margin)

    is_sufficient = estimated_mb <= effective_available

    return is_sufficient, {
        "estimated_mb": estimated_mb,
        "available_mb": available,
        "total_mb": vram["total_mb"],
        "safety_margin_mb": margin,
        "effective_available_mb": effective_available,
        "is_sufficient": is_sufficient,
    }
