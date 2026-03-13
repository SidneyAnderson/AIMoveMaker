"""Video generation pipeline — LTX-V 2.3, WAN 2.2.

Supports T2V (text-to-video), I2V (image-to-video), V2V (video-to-video).
Uses HuggingFace Diffusers for all video inference.
"""
import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from loguru import logger


@dataclass
class VideoGenResult:
    """Result of a video generation job."""
    output_path: str
    width: int
    height: int
    frames: int
    fps: int
    duration_ms: int
    seed_used: int
    file_size_bytes: int
    mime_type: str = "video/mp4"


class VideoPipeline:
    """Manages Diffusers video pipelines for LTX-V and WAN 2.2."""

    def __init__(self):
        self._pipe = None
        self._current_model_path: str | None = None

    def _get_torch_dtype(self, precision: str):
        import torch
        return {
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
            "fp32": torch.float32,
        }.get(precision, torch.float16)

    def _load_pipeline(
        self,
        model_path: str,
        architecture: str,
        mode: str,
        precision: str = "fp16",
        use_xformers: bool = False,
    ):
        """Load or reuse a video pipeline."""
        import torch

        cache_key = f"{model_path}:{architecture}:{mode}"
        if self._pipe is not None and self._current_model_path == cache_key:
            return

        logger.info(
            f"Loading video pipeline: model={model_path}, "
            f"arch={architecture}, mode={mode}, precision={precision}"
        )

        dtype = self._get_torch_dtype(precision)

        if architecture == "ltxv":
            self._load_ltxv(model_path, mode, dtype)
        elif architecture == "wan":
            self._load_wan(model_path, mode, dtype)
        else:
            # Generic video pipeline attempt
            self._load_generic(model_path, mode, dtype)

        if self._pipe is not None:
            self._pipe.to("cuda")
            if use_xformers:
                try:
                    self._pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    logger.debug("xformers not available for video pipeline")
            self._current_model_path = cache_key

    def _load_ltxv(self, model_path: str, mode: str, dtype):
        """Load LTX-Video pipeline."""
        try:
            from diffusers import LTXPipeline, LTXImageToVideoPipeline

            if mode in ("t2v",):
                self._pipe = LTXPipeline.from_pretrained(
                    model_path, torch_dtype=dtype
                )
            else:  # i2v, v2v
                self._pipe = LTXImageToVideoPipeline.from_pretrained(
                    model_path, torch_dtype=dtype
                )
        except ImportError:
            logger.warning("LTX pipeline classes not available in this diffusers version")
            self._load_generic(model_path, mode, dtype)

    def _load_wan(self, model_path: str, mode: str, dtype):
        """Load WAN 2.2 pipeline."""
        try:
            from diffusers import WanPipeline, WanImageToVideoPipeline

            if mode == "t2v":
                self._pipe = WanPipeline.from_pretrained(
                    model_path, torch_dtype=dtype
                )
            else:  # i2v, v2v
                self._pipe = WanImageToVideoPipeline.from_pretrained(
                    model_path, torch_dtype=dtype
                )
        except ImportError:
            logger.warning("WAN pipeline classes not available in this diffusers version")
            self._load_generic(model_path, mode, dtype)

    def _load_generic(self, model_path: str, mode: str, dtype):
        """Fallback generic video pipeline."""
        try:
            from diffusers import DiffusionPipeline
            self._pipe = DiffusionPipeline.from_pretrained(
                model_path, torch_dtype=dtype
            )
        except Exception as e:
            logger.error(f"Failed to load video pipeline: {e}")
            self._pipe = None

    def _load_loras(self, lora_stack: list[dict]):
        """Load LoRA weights onto the pipeline."""
        if not lora_stack or self._pipe is None:
            return
        for lora in lora_stack:
            lora_path = lora.get("storage_path") or lora.get("lora_id", "")
            weight = lora.get("weight", 1.0)
            try:
                self._pipe.load_lora_weights(lora_path)
                self._pipe.fuse_lora(lora_scale=weight)
                logger.info(f"Loaded video LoRA: {lora_path} (weight={weight})")
            except Exception as e:
                logger.warning(f"Failed to load video LoRA {lora_path}: {e}")

    def generate(
        self,
        model_path: str,
        architecture: str,
        mode: str,
        positive_prompt: str,
        negative_prompt: str = "",
        source_image_path: str | None = None,
        source_video_path: str | None = None,
        width: int = 1280,
        height: int = 720,
        frames: int = 49,
        fps: int = 24,
        steps: int = 30,
        cfg_scale: float = 7.0,
        motion_strength: float | None = None,
        seed: int = -1,
        lora_stack: list[dict] | None = None,
        output_dir: str = "/tmp",
        precision: str = "fp16",
        use_xformers: bool = False,
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> VideoGenResult:
        """Generate video using the configured pipeline."""
        import torch

        self._load_pipeline(model_path, architecture, mode, precision, use_xformers)
        if lora_stack:
            self._load_loras(lora_stack)

        actual_seed = seed if seed != -1 else torch.randint(0, 2**32, (1,)).item()
        generator = torch.Generator(device="cuda").manual_seed(actual_seed)

        gen_kwargs: dict[str, Any] = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt or None,
            "num_frames": frames,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "generator": generator,
        }

        # Add source image for I2V
        if mode in ("i2v", "v2v") and source_image_path:
            from PIL import Image
            gen_kwargs["image"] = Image.open(source_image_path).convert("RGB")

        if motion_strength is not None:
            gen_kwargs["motion_strength"] = motion_strength

        # Progress callback
        if progress_callback:
            def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
                progress_callback(step_index + 1, steps)
                return callback_kwargs
            gen_kwargs["callback_on_step_end"] = callback_on_step_end

        result = self._pipe(**gen_kwargs)

        # Export to MP4
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(output_dir, filename)

        # diffusers video output → export frames to mp4
        self._export_to_mp4(result, output_path, fps)
        file_size = os.path.getsize(output_path)
        duration_ms = int(frames / fps * 1000)

        return VideoGenResult(
            output_path=output_path,
            width=width,
            height=height,
            frames=frames,
            fps=fps,
            duration_ms=duration_ms,
            seed_used=actual_seed,
            file_size_bytes=file_size,
        )

    def _export_to_mp4(self, result, output_path: str, fps: int):
        """Export diffusers video output to MP4 file."""
        try:
            from diffusers.utils import export_to_video
            # diffusers utility for exporting generated frames
            if hasattr(result, "frames"):
                frames = result.frames
                if isinstance(frames, list) and len(frames) > 0:
                    if isinstance(frames[0], list):
                        frames = frames[0]  # Unwrap nested list
                    export_to_video(frames, output_path, fps=fps)
                    return
        except ImportError:
            pass

        # Fallback: use ffmpeg to encode frames
        try:
            import numpy as np
            import subprocess
            import tempfile

            frames = result.frames if hasattr(result, "frames") else []
            if isinstance(frames, list) and len(frames) > 0:
                if isinstance(frames[0], list):
                    frames = frames[0]

                with tempfile.TemporaryDirectory() as tmp_dir:
                    for i, frame in enumerate(frames):
                        if hasattr(frame, "save"):
                            frame.save(os.path.join(tmp_dir, f"frame_{i:06d}.png"))

                    subprocess.run(
                        [
                            "ffmpeg", "-y",
                            "-framerate", str(fps),
                            "-i", os.path.join(tmp_dir, "frame_%06d.png"),
                            "-c:v", "libx264",
                            "-pix_fmt", "yuv420p",
                            output_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
        except Exception as e:
            logger.error(f"Failed to export video to MP4: {e}")
            raise

    def unload(self):
        """Free GPU memory."""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
            self._current_model_path = None
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass


# Singleton
_video_pipeline = VideoPipeline()


def get_video_pipeline() -> VideoPipeline:
    return _video_pipeline
