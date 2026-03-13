"""Image generation pipeline — T2I, I2I, Inpaint, Outpaint.

Uses HuggingFace Diffusers for all image inference.
No ComfyUI dependency.

PRD Section 10.1 Open Items:
  - Real-ESRGAN upscaling: Canvas Resize tool references Real-ESRGAN
    "if model registered". This is DEFERRED to v2 — the outpaint method uses
    standard Diffusers inpainting rather than a dedicated upscaling model.
    To add in v2: register Real-ESRGAN in ModelRegistry, add upscale() method
    that loads the model and processes images. See PRD Section 10.1 Item 2.
"""
import os
import random
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from loguru import logger


@dataclass
class ImageGenResult:
    """Result of an image generation job."""
    output_path: str
    width: int
    height: int
    seed_used: int
    file_size_bytes: int
    mime_type: str = "image/png"


def _resolve_seed(seed: int, seed_mode: str, index: int = 0) -> int:
    """Resolve seed based on mode."""
    if seed_mode == "random" or seed == -1:
        return random.randint(0, 2**32 - 1)
    if seed_mode == "variation":
        return seed + index
    return seed  # fixed


def _get_torch_dtype(precision: str):
    """Get torch dtype from precision string."""
    import torch
    return {
        "fp16": torch.float16,
        "bf16": torch.bfloat16,
        "fp32": torch.float32,
    }.get(precision, torch.float16)


class ImagePipeline:
    """Manages Diffusers image pipelines with model loading and inference."""

    def __init__(self):
        self._pipe = None
        self._current_model_path: str | None = None
        self._controlnet_pipe = None

    def _load_pipeline(
        self,
        model_path: str,
        mode: str,
        precision: str = "fp16",
        use_xformers: bool = False,
        controlnet_path: str | None = None,
    ):
        """Load or reuse a Diffusers pipeline."""
        import torch
        from diffusers import (
            AutoPipelineForImage2Image,
            AutoPipelineForInpainting,
            AutoPipelineForText2Image,
            ControlNetModel,
            StableDiffusionControlNetPipeline,
        )

        dtype = _get_torch_dtype(precision)

        # Reuse if same model already loaded for same mode
        if self._pipe is not None and self._current_model_path == f"{model_path}:{mode}":
            return

        logger.info(f"Loading image pipeline: model={model_path}, mode={mode}, precision={precision}")

        if controlnet_path and mode == "t2i":
            # ControlNet pipeline
            controlnet = ControlNetModel.from_pretrained(
                controlnet_path, torch_dtype=dtype
            )
            self._pipe = StableDiffusionControlNetPipeline.from_pretrained(
                model_path,
                controlnet=controlnet,
                torch_dtype=dtype,
                safety_checker=None,
            )
        elif mode == "t2i":
            self._pipe = AutoPipelineForText2Image.from_pretrained(
                model_path, torch_dtype=dtype, safety_checker=None,
            )
        elif mode == "i2i":
            self._pipe = AutoPipelineForImage2Image.from_pretrained(
                model_path, torch_dtype=dtype, safety_checker=None,
            )
        elif mode in ("inpaint", "outpaint"):
            self._pipe = AutoPipelineForInpainting.from_pretrained(
                model_path, torch_dtype=dtype, safety_checker=None,
            )

        if self._pipe is not None:
            self._pipe.to("cuda")
            if use_xformers:
                try:
                    self._pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    logger.debug("xformers not available, skipping")
            self._current_model_path = f"{model_path}:{mode}"

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
                logger.info(f"Loaded LoRA: {lora_path} (weight={weight})")
            except Exception as e:
                logger.warning(f"Failed to load LoRA {lora_path}: {e}")

    def generate_t2i(
        self,
        model_path: str,
        positive_prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.0,
        seed: int = -1,
        seed_mode: str = "random",
        sampler: str | None = None,
        scheduler: str | None = None,
        lora_stack: list[dict] | None = None,
        output_dir: str = "/tmp",
        precision: str = "fp16",
        use_xformers: bool = False,
        progress_callback: Callable | None = None,
        controlnet_path: str | None = None,
        controlnet_image=None,
        controlnet_strength: float = 1.0,
        **kwargs,
    ) -> ImageGenResult:
        """Text-to-Image generation."""
        import torch

        self._load_pipeline(
            model_path, "t2i", precision, use_xformers,
            controlnet_path=controlnet_path
        )
        if lora_stack:
            self._load_loras(lora_stack)

        actual_seed = _resolve_seed(seed, seed_mode)
        generator = torch.Generator(device="cuda").manual_seed(actual_seed)

        if scheduler:
            self._set_scheduler(scheduler)

        gen_kwargs: dict[str, Any] = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt or None,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "generator": generator,
        }

        if controlnet_image is not None:
            gen_kwargs["image"] = controlnet_image
            gen_kwargs["controlnet_conditioning_scale"] = controlnet_strength

        # Progress callback wrapper
        if progress_callback:
            def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
                progress_callback(step_index + 1, steps)
                return callback_kwargs
            gen_kwargs["callback_on_step_end"] = callback_on_step_end

        result = self._pipe(**gen_kwargs)
        image = result.images[0]

        # Save output
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        output_path = os.path.join(output_dir, filename)
        image.save(output_path)
        file_size = os.path.getsize(output_path)

        return ImageGenResult(
            output_path=output_path,
            width=width,
            height=height,
            seed_used=actual_seed,
            file_size_bytes=file_size,
        )

    def generate_i2i(
        self,
        model_path: str,
        positive_prompt: str,
        source_image_path: str,
        negative_prompt: str = "",
        denoise_strength: float = 0.75,
        steps: int = 30,
        cfg_scale: float = 7.0,
        seed: int = -1,
        seed_mode: str = "random",
        lora_stack: list[dict] | None = None,
        output_dir: str = "/tmp",
        precision: str = "fp16",
        use_xformers: bool = False,
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> ImageGenResult:
        """Image-to-Image generation."""
        import torch
        from PIL import Image

        self._load_pipeline(model_path, "i2i", precision, use_xformers)
        if lora_stack:
            self._load_loras(lora_stack)

        source = Image.open(source_image_path).convert("RGB")
        actual_seed = _resolve_seed(seed, seed_mode)
        generator = torch.Generator(device="cuda").manual_seed(actual_seed)

        gen_kwargs: dict[str, Any] = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt or None,
            "image": source,
            "strength": denoise_strength,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "generator": generator,
        }

        if progress_callback:
            actual_steps = int(steps * denoise_strength)
            def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
                progress_callback(step_index + 1, actual_steps)
                return callback_kwargs
            gen_kwargs["callback_on_step_end"] = callback_on_step_end

        result = self._pipe(**gen_kwargs)
        image = result.images[0]

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        output_path = os.path.join(output_dir, filename)
        image.save(output_path)
        file_size = os.path.getsize(output_path)

        return ImageGenResult(
            output_path=output_path,
            width=image.width,
            height=image.height,
            seed_used=actual_seed,
            file_size_bytes=file_size,
            mime_type="image/png",
        )

    def generate_inpaint(
        self,
        model_path: str,
        positive_prompt: str,
        source_image_path: str,
        mask_image_path: str,
        negative_prompt: str = "",
        denoise_strength: float = 1.0,
        steps: int = 30,
        cfg_scale: float = 7.0,
        seed: int = -1,
        seed_mode: str = "random",
        lora_stack: list[dict] | None = None,
        output_dir: str = "/tmp",
        precision: str = "fp16",
        use_xformers: bool = False,
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> ImageGenResult:
        """Inpainting — redraws masked region guided by prompt."""
        import torch
        from PIL import Image

        self._load_pipeline(model_path, "inpaint", precision, use_xformers)
        if lora_stack:
            self._load_loras(lora_stack)

        source = Image.open(source_image_path).convert("RGB")
        mask = Image.open(mask_image_path).convert("L")
        actual_seed = _resolve_seed(seed, seed_mode)
        generator = torch.Generator(device="cuda").manual_seed(actual_seed)

        gen_kwargs: dict[str, Any] = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt or None,
            "image": source,
            "mask_image": mask,
            "strength": denoise_strength,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "generator": generator,
        }

        if progress_callback:
            def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
                progress_callback(step_index + 1, steps)
                return callback_kwargs
            gen_kwargs["callback_on_step_end"] = callback_on_step_end

        result = self._pipe(**gen_kwargs)
        image = result.images[0]

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        output_path = os.path.join(output_dir, filename)
        image.save(output_path)
        file_size = os.path.getsize(output_path)

        return ImageGenResult(
            output_path=output_path,
            width=image.width,
            height=image.height,
            seed_used=actual_seed,
            file_size_bytes=file_size,
        )

    def generate_outpaint(
        self,
        model_path: str,
        positive_prompt: str,
        source_image_path: str,
        expand_direction: str = "right",
        expand_amount: int = 256,
        negative_prompt: str = "",
        steps: int = 30,
        cfg_scale: float = 7.0,
        seed: int = -1,
        seed_mode: str = "random",
        lora_stack: list[dict] | None = None,
        output_dir: str = "/tmp",
        precision: str = "fp16",
        use_xformers: bool = False,
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> ImageGenResult:
        """Outpainting — extends image beyond original borders."""
        import torch
        from PIL import Image

        self._load_pipeline(model_path, "inpaint", precision, use_xformers)
        if lora_stack:
            self._load_loras(lora_stack)

        source = Image.open(source_image_path).convert("RGB")
        w, h = source.size

        # Determine new canvas size and paste position
        directions = {
            "right": (w + expand_amount, h, 0, 0),
            "left": (w + expand_amount, h, expand_amount, 0),
            "down": (w, h + expand_amount, 0, 0),
            "up": (w, h + expand_amount, 0, expand_amount),
        }
        new_w, new_h, paste_x, paste_y = directions.get(
            expand_direction, (w + expand_amount, h, 0, 0)
        )

        # Create expanded canvas with source pasted and mask for new region
        canvas = Image.new("RGB", (new_w, new_h), (0, 0, 0))
        canvas.paste(source, (paste_x, paste_y))

        mask = Image.new("L", (new_w, new_h), 255)  # White = inpaint region
        mask_paste = Image.new("L", (w, h), 0)  # Black = keep
        mask.paste(mask_paste, (paste_x, paste_y))

        actual_seed = _resolve_seed(seed, seed_mode)
        generator = torch.Generator(device="cuda").manual_seed(actual_seed)

        gen_kwargs: dict[str, Any] = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt or None,
            "image": canvas,
            "mask_image": mask,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "generator": generator,
            "width": new_w,
            "height": new_h,
        }

        if progress_callback:
            def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
                progress_callback(step_index + 1, steps)
                return callback_kwargs
            gen_kwargs["callback_on_step_end"] = callback_on_step_end

        result = self._pipe(**gen_kwargs)
        image = result.images[0]

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        output_path = os.path.join(output_dir, filename)
        image.save(output_path)
        file_size = os.path.getsize(output_path)

        return ImageGenResult(
            output_path=output_path,
            width=new_w,
            height=new_h,
            seed_used=actual_seed,
            file_size_bytes=file_size,
        )

    def _set_scheduler(self, scheduler_name: str):
        """Set the scheduler on the pipeline."""
        if self._pipe is None:
            return
        try:
            from diffusers import (
                DDIMScheduler,
                DPMSolverMultistepScheduler,
                EulerAncestralDiscreteScheduler,
                EulerDiscreteScheduler,
                PNDMScheduler,
            )
            schedulers = {
                "euler": EulerDiscreteScheduler,
                "euler_a": EulerAncestralDiscreteScheduler,
                "dpm++": DPMSolverMultistepScheduler,
                "ddim": DDIMScheduler,
                "pndm": PNDMScheduler,
            }
            sched_cls = schedulers.get(scheduler_name.lower())
            if sched_cls:
                self._pipe.scheduler = sched_cls.from_config(
                    self._pipe.scheduler.config
                )
        except Exception as e:
            logger.warning(f"Failed to set scheduler {scheduler_name}: {e}")

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
_image_pipeline = ImagePipeline()


def get_image_pipeline() -> ImagePipeline:
    return _image_pipeline
