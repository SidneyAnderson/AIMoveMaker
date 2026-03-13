"""ControlNet pipeline wrappers.

Supports: depth, canny, pose, reference control types.
ControlNet is available on Keyframes (image generation) and VideoClips (video generation).
"""
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class ControlNetConfig:
    """ControlNet configuration per PRD Table 14."""
    cn_enabled: bool = False
    cn_type: str | None = None      # depth, canny, pose, reference
    cn_control_asset_path: str | None = None
    cn_strength: float = 1.0        # conditioning_scale 0.0-2.0
    cn_start_pct: float = 0.0       # guidance start
    cn_end_pct: float = 1.0         # guidance end


# ControlNet model identifiers per type
CONTROLNET_MODELS = {
    "depth": "lllyasviel/control_v11f1p_sd15_depth",
    "canny": "lllyasviel/control_v11p_sd15_canny",
    "pose": "lllyasviel/control_v11p_sd15_openpose",
    "reference": None,  # Reference uses IP-Adapter, not ControlNet
}

# SDXL ControlNet models
CONTROLNET_MODELS_SDXL = {
    "depth": "diffusers/controlnet-depth-sdxl-1.0",
    "canny": "diffusers/controlnet-canny-sdxl-1.0",
    "pose": "thibaud/controlnet-openpose-sdxl-1.0",
    "reference": None,
}


def get_controlnet_model_id(cn_type: str, architecture: str = "sd15") -> str | None:
    """Get the ControlNet model identifier for the given type and architecture."""
    if architecture in ("sdxl", "flux"):
        return CONTROLNET_MODELS_SDXL.get(cn_type)
    return CONTROLNET_MODELS.get(cn_type)


def preprocess_control_image(
    image_path: str,
    cn_type: str,
    width: int | None = None,
    height: int | None = None,
):
    """Preprocess a control image based on the ControlNet type.

    Returns the processed control image ready for the ControlNet pipeline.
    """
    from PIL import Image

    image = Image.open(image_path).convert("RGB")

    if width and height:
        image = image.resize((width, height), Image.LANCZOS)

    if cn_type == "canny":
        return _process_canny(image)
    elif cn_type == "depth":
        return _process_depth(image)
    elif cn_type == "pose":
        return _process_pose(image)
    elif cn_type == "reference":
        return image  # Reference image used as-is
    else:
        logger.warning(f"Unknown ControlNet type: {cn_type}, returning raw image")
        return image


def _process_canny(image):
    """Extract Canny edges from image."""
    try:
        import cv2
        import numpy as np
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        # Convert back to 3-channel RGB
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        from PIL import Image as PILImage
        return PILImage.fromarray(edges_rgb)
    except ImportError:
        logger.warning("cv2 not available for canny processing, using raw image")
        return image


def _process_depth(image):
    """Estimate depth map from image using MiDaS or similar."""
    try:
        import torch
        from transformers import DPTForDepthEstimation, DPTImageProcessor

        processor = DPTImageProcessor.from_pretrained("Intel/dpt-hybrid-midas")
        model = DPTForDepthEstimation.from_pretrained("Intel/dpt-hybrid-midas")

        inputs = processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = model(**inputs)
            predicted_depth = outputs.predicted_depth

        # Normalize to 0-255
        import numpy as np
        depth = predicted_depth.squeeze().cpu().numpy()
        depth = (depth - depth.min()) / (depth.max() - depth.min()) * 255
        depth = depth.astype(np.uint8)

        from PIL import Image as PILImage
        depth_image = PILImage.fromarray(depth)
        depth_image = depth_image.resize(image.size, PILImage.LANCZOS)
        # Convert to RGB
        return depth_image.convert("RGB")
    except ImportError:
        logger.warning("transformers/DPT not available for depth estimation, using raw image")
        return image


def _process_pose(image):
    """Extract pose skeleton from image."""
    try:
        from controlnet_aux import OpenposeDetector

        openpose = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
        pose_image = openpose(image)
        return pose_image
    except ImportError:
        logger.warning("controlnet_aux not available for pose estimation, using raw image")
        return image


def load_controlnet_model(cn_type: str, architecture: str = "sd15", precision: str = "fp16"):
    """Load a ControlNet model for use with a diffusion pipeline.

    Returns a ControlNetModel instance.
    """
    import torch
    from diffusers import ControlNetModel

    model_id = get_controlnet_model_id(cn_type, architecture)
    if model_id is None:
        raise ValueError(f"No ControlNet model available for type={cn_type}, arch={architecture}")

    dtype = {
        "fp16": torch.float16,
        "bf16": torch.bfloat16,
        "fp32": torch.float32,
    }.get(precision, torch.float16)

    logger.info(f"Loading ControlNet model: {model_id} ({precision})")
    controlnet = ControlNetModel.from_pretrained(model_id, torch_dtype=dtype)
    return controlnet


def build_controlnet_kwargs(config: ControlNetConfig) -> dict[str, Any]:
    """Build kwargs dict for ControlNet pipeline calls.

    Returns kwargs to merge into the pipeline's generate() call.
    """
    if not config.cn_enabled or not config.cn_control_asset_path:
        return {}

    control_image = preprocess_control_image(
        config.cn_control_asset_path,
        config.cn_type or "canny",
    )

    return {
        "image": control_image,
        "controlnet_conditioning_scale": config.cn_strength,
        "control_guidance_start": config.cn_start_pct,
        "control_guidance_end": config.cn_end_pct,
    }
