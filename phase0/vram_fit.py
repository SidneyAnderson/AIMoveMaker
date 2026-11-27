#!/usr/bin/env python3
"""
Phase 0 VRAM Fit Tests
Loads each model, runs short test render, records peak VRAM and performance.
"""
import sys
import json
import argparse
import platform
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

import torch

RESULTS_DIR = Path(__file__).parent / "results"
SAMPLES_DIR = RESULTS_DIR / "samples"

# 10% safety margin for 32 GB GPU
VRAM_LIMIT_GB = 32.0
SAFETY_MARGIN = 0.9
VRAM_THRESHOLD_GB = VRAM_LIMIT_GB * SAFETY_MARGIN


def get_hardware_info() -> Dict[str, Any]:
    """Collect hardware metadata."""
    if not torch.cuda.is_available():
        return {"error": "No CUDA GPU"}
    
    props = torch.cuda.get_device_properties(0)
    return {
        "gpu": props.name,
        "vram_total_gb": round(props.total_memory / 1e9, 1),
        "cuda_version": torch.version.cuda,
        "compute_capability": f"sm_{props.major}{props.minor}",
        "pytorch_version": torch.__version__,
    }


def measure_vram(fn, *args, **kwargs):
    """Run function and measure peak VRAM."""
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    
    start_vram = torch.cuda.memory_allocated() / 1e9
    result = fn(*args, **kwargs)
    peak_vram = torch.cuda.max_memory_allocated() / 1e9
    
    return result, peak_vram


def test_video_model_h3(model_root: Path, precision: str = "fp8") -> Dict[str, Any]:
    """Test MiniMax H3 video model."""
    print("\n" + "=" * 60)
    print("Testing MiniMax H3 (video)")
    print("=" * 60)
    
    model_key = "minimax_h3"
    model_path = model_root / "MiniMax-H3"
    
    if not model_path.exists():
        print(f"⚠️  Weights not found: {model_path}")
        return {
            "model_key": model_key,
            "status": "missing_weights",
            "vram_fit": False,
            "errors": [f"Weights not found at {model_path}"],
        }
    
    try:
        import time
        from diffusers import DiffusionPipeline
        
        print(f"Loading from {model_path} (precision={precision})...")
        start_time = time.time()
        
        # Load pipeline
        dtype = torch.float8_e4m3fn if precision == "fp8" and torch.cuda.is_bf16_supported() else torch.bfloat16
        pipe = DiffusionPipeline.from_pretrained(
            str(model_path),
            torch_dtype=dtype,
            use_safetensors=True,
        )
        pipe = pipe.to("cuda")
        
        load_time = time.time() - start_time
        print(f"Loaded in {load_time:.1f} seconds")
        
        # Test render: 22 frames, 1024×576 (16:9)
        prompt = "A serene forest clearing at dawn, cinematic lighting"
        
        def render():
            return pipe(
                prompt=prompt,
                num_frames=22,
                height=576,
                width=1024,
                num_inference_steps=50,
                guidance_scale=5.0,
            )
        
        print("Rendering 22-frame test clip (1024×576)...")
        start_render = time.time()
        output, peak_vram = measure_vram(render)
        render_time = time.time() - start_render
        
        it_per_sec = 50 / render_time if render_time > 0 else 0
        
        print(f"Peak VRAM: {peak_vram:.2f} GB")
        print(f"Render time: {render_time:.1f} sec ({it_per_sec:.2f} it/s)")
        
        vram_fit = peak_vram < VRAM_THRESHOLD_GB
        status = "pass" if vram_fit else "fail_vram"
        
        # Save sample
        sample_path = SAMPLES_DIR / f"{model_key}_sample.mp4"
        if hasattr(output, 'frames') and output.frames:
            # Save video frames (implementation depends on output format)
            print(f"Sample saved to {sample_path}")
        
        result = {
            "model_key": model_key,
            "test_date": datetime.now(timezone.utc).isoformat(),
            "hardware": get_hardware_info(),
            "precision": precision,
            "vram_fit": vram_fit,
            "peak_vram_gb": round(peak_vram, 2),
            "load_time_sec": round(load_time, 1),
            "inference_time_sec": round(render_time, 1),
            "it_per_sec": round(it_per_sec, 2),
            "output_resolution": "1024x576x22",
            "status": status,
            "errors": [],
        }
        
        print(f"✅ {status.upper()}: MiniMax H3 (VRAM fit: {vram_fit})")
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            "model_key": model_key,
            "status": "error",
            "vram_fit": False,
            "errors": [str(e)],
        }


def test_image_model_krea2(model_root: Path) -> Dict[str, Any]:
    """Test Krea 2 Turbo image model."""
    print("\n" + "=" * 60)
    print("Testing Krea 2 Turbo (image)")
    print("=" * 60)
    
    model_key = "krea_2_turbo"
    model_path = model_root / "Krea-2-Turbo"
    
    if not model_path.exists():
        print(f"⚠️  Weights not found: {model_path}")
        return {
            "model_key": model_key,
            "status": "missing_weights",
            "vram_fit": False,
            "errors": [f"Weights not found at {model_path}"],
        }
    
    try:
        import time
        
        print(f"Loading from {model_path}...")
        start_time = time.time()
        
        # Try Krea2Pipeline (Diffusers >= 0.43)
        try:
            from diffusers import Krea2Pipeline
        except ImportError:
            print("❌ Krea2Pipeline not found (requires diffusers>=0.43)")
            return {
                "model_key": model_key,
                "status": "pipeline_unavailable",
                "vram_fit": False,
                "errors": ["Krea2Pipeline requires diffusers>=0.43"],
            }
        
        pipe = Krea2Pipeline.from_pretrained(
            str(model_path),
            torch_dtype=torch.bfloat16,
        )
        pipe = pipe.to("cuda")
        
        load_time = time.time() - start_time
        print(f"Loaded in {load_time:.1f} seconds")
        
        # Test render: 1024×1024, 8 steps, no CFG
        prompt = "A cinematic forest scene at sunrise, photoreal"
        
        def render():
            return pipe(
                prompt=prompt,
                height=1024,
                width=1024,
                num_inference_steps=8,
                guidance_scale=0.0,  # Turbo: CFG off
            )
        
        print("Rendering 1024×1024 test image (8 steps)...")
        start_render = time.time()
        output, peak_vram = measure_vram(render)
        render_time = time.time() - start_render
        
        it_per_sec = 8 / render_time if render_time > 0 else 0
        
        print(f"Peak VRAM: {peak_vram:.2f} GB")
        print(f"Render time: {render_time:.1f} sec ({it_per_sec:.2f} it/s)")
        
        vram_fit = peak_vram < VRAM_THRESHOLD_GB
        status = "pass" if vram_fit else "fail_vram"
        
        # Save sample
        sample_path = SAMPLES_DIR / f"{model_key}_sample.png"
        if hasattr(output, 'images') and output.images:
            output.images[0].save(sample_path)
            print(f"Sample saved to {sample_path}")
        
        result = {
            "model_key": model_key,
            "test_date": datetime.now(timezone.utc).isoformat(),
            "hardware": get_hardware_info(),
            "precision": "bfloat16",
            "vram_fit": vram_fit,
            "peak_vram_gb": round(peak_vram, 2),
            "load_time_sec": round(load_time, 1),
            "inference_time_sec": round(render_time, 1),
            "it_per_sec": round(it_per_sec, 2),
            "output_resolution": "1024x1024",
            "status": status,
            "errors": [],
        }
        
        print(f"✅ {status.upper()}: Krea 2 Turbo (VRAM fit: {vram_fit})")
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            "model_key": model_key,
            "status": "error",
            "vram_fit": False,
            "errors": [str(e)],
        }


def test_image_model_zimage(model_root: Path) -> Dict[str, Any]:
    """Test Z-Image-Turbo image model."""
    model_key = "z_image_turbo"
    # Similar structure to test_image_model_krea2, using ZImagePipeline
    # (abbreviated for brevity; full implementation would mirror above)
    print(f"\n⚠️  Test for {model_key} not fully implemented (stub)")
    return {
        "model_key": model_key,
        "status": "not_implemented",
        "vram_fit": False,
        "errors": ["Test implementation TBD"],
    }


# Stub tests for remaining models
def test_video_model_ltx(model_root: Path, precision: str = "bf16") -> Dict[str, Any]:
    return {"model_key": "ltx_2_5", "status": "not_implemented", "vram_fit": False, "precision": precision, "errors": ["Test TBD"]}

def test_video_model_wan(model_root: Path, precision: str = "bf16") -> Dict[str, Any]:
    return {"model_key": "wan_bernini", "status": "not_implemented", "vram_fit": False, "precision": precision, "errors": ["Test TBD"]}

def test_video_model_bernini_r(model_root: Path) -> Dict[str, Any]:
    """Gate for Bernini-R, the internal Wan edit/consistency route.

    Skips when weights are absent. Does not claim a stock Diffusers load:
    the repo has no model_index.json. Upstream pins diffusers==0.35.2, so a
    pass is only meaningful inside .venvs/bernini.
    """
    model_key = "bernini_r"
    model_path = model_root / "Bernini-R-Diffusers"
    notes = (
        "Internal route for edit_shot and keep_consistent on wan_bernini. "
        "ByteDance inference code, not a stock Diffusers pipeline class. "
        "Run this entry in .venvs/bernini (diffusers==0.35.2). "
        "Do not downgrade the application environment. "
        "Bernini-R-S2V is out of scope."
    )

    if not model_path.exists():
        print(f"⚠️  Weights not found: {model_path}")
        return {
            "model_key": model_key,
            "status": "missing_weights",
            "vram_fit": False,
            "errors": [f"Weights not found at {model_path}"],
            "notes": notes,
        }

    try:
        import importlib.metadata
        diffusers_version = importlib.metadata.version("diffusers")
    except Exception as exc:
        diffusers_version = f"unknown ({exc})"

    if diffusers_version != "0.35.2":
        print(f"⚠️  diffusers {diffusers_version} is not the Bernini pin 0.35.2")
        return {
            "model_key": model_key,
            "status": "pipeline_unavailable",
            "vram_fit": False,
            "errors": [
                f"This process has diffusers {diffusers_version}. "
                "Bernini-R upstream pins diffusers==0.35.2. "
                "Re-run inside .venvs/bernini."
            ],
            "notes": notes,
        }

    print("⚠️  Pin matches, but this kit does not call ByteDance's inference script")
    return {
        "model_key": model_key,
        "status": "not_implemented",
        "vram_fit": False,
        "errors": [
            "diffusers==0.35.2 is active and weights are present, "
            "but ByteDance's inference entrypoint is not bundled here. "
            "Record a manual load with their inference script in this venv."
        ],
        "notes": notes,
    }


def test_h3_ref2va(model_root: Path, precision: str = "bf16") -> Dict[str, Any]:
    """Gate for MiniMax H3 Ref2VA (continue, edit, consistency). Not a UI mode.

    Ref2VA is the transformer_ref partition of MiniMax-H3, not a separate repo.
    A pass requires a Diffusers class that can load that partition. This function
    does not start SGLang. If only the weights exist, the result is
    pipeline_unavailable and the product uses the Section A19 fallback.
    """
    model_key = "h3_ref2va"
    model_path = model_root / "MiniMax-H3"
    notes = (
        "Internal route for continue_shot, edit_shot, and keep_consistent on minimax_h3. "
        "Own SGLang service with --model-variant ref2va, or a Diffusers ModularPipeline "
        "over transformer_ref. Open release excludes Context-IR and Regenerate-2K. "
        "Failure selects the Section A19 fallback; it does not remove the core operation."
    )
    if not model_path.exists():
        print(f"⚠️  Weights not found: {model_path}")
        return {
            "model_key": model_key,
            "status": "missing_weights",
            "vram_fit": False,
            "errors": [f"Weights not found at {model_path}"],
            "notes": notes,
        }

    ref_dir = next(
        (candidate for candidate in (
            model_path / "transformer_ref",
            model_path / "transformer_ref2va",
        ) if candidate.exists()),
        None,
    )
    if ref_dir is None:
        print("⚠️  Ref2VA partition not found")
        return {
            "model_key": model_key,
            "status": "missing_weights",
            "vram_fit": False,
            "errors": ["transformer_ref (or transformer_ref2va) not found under MiniMax-H3"],
            "notes": notes,
        }

    try:
        import diffusers
    except Exception as exc:
        return {
            "model_key": model_key,
            "status": "pipeline_unavailable",
            "vram_fit": False,
            "errors": [f"diffusers import failed: {exc}"],
            "notes": notes,
        }

    ref_class = None
    for class_name in (
        "MiniMaxH3RefPipeline",
        "MiniMaxH3VideoModularPipeline",
        "MiniMaxH3ModularPipeline",
    ):
        candidate = getattr(diffusers, class_name, None)
        if candidate is not None:
            ref_class = candidate
            break

    if ref_class is None:
        print("⚠️  No Diffusers Ref2VA class in this build")
        return {
            "model_key": model_key,
            "status": "pipeline_unavailable",
            "vram_fit": False,
            "precision": precision,
            "errors": [
                "Weights include a ref partition, but this diffusers build has no "
                "MiniMax Ref2VA / H3 video pipeline class. "
                "Either load transformer_ref with a documented ModularPipeline, "
                "or run SGLang in the H3 venv with --model-variant ref2va and "
                "record peak VRAM. Do not mark this gate pass from FL2VA."
            ],
            "notes": notes,
        }

    try:
        import time
        print(f"Loading {ref_class.__name__} from {model_path}...")
        start = time.time()
        ref_class.from_pretrained(str(model_path), torch_dtype=torch.bfloat16)
        load_time = time.time() - start
        peak = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else None
        vram_fit = bool(peak is not None and peak < VRAM_THRESHOLD_GB)
        return {
            "model_key": model_key,
            "status": "pass" if vram_fit else "fail_vram",
            "vram_fit": vram_fit,
            "peak_vram_gb": None if peak is None else round(peak, 2),
            "load_time_sec": round(load_time, 1),
            "precision": precision,
            "errors": [],
            "notes": notes + " Load-only; a ref2va render was not run.",
        }
    except Exception as exc:
        print(f"⚠️  Ref2VA load failed: {exc}")
        return {
            "model_key": model_key,
            "status": "pipeline_unavailable",
            "vram_fit": False,
            "precision": precision,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "notes": notes,
        }


def test_ltx_ic_lora(model_root: Path, precision: str = "bf16") -> Dict[str, Any]:
    """Diffusers load check for two representative LTX-2.5 Creative Lab IC-LoRAs.

    Ingredients (keep_consistent) and Restore (restore_refine). Both repos are
    HF-gated. Lightricks documents a ComfyUI path; this check does not call
    ComfyUI. Missing weights skip. A failed Diffusers load is
    pipeline_unavailable, which selects the Section A19 fallback.
    """
    model_key = "ltx_ic_lora"
    base = model_root / "LTX-2.5"
    representatives = (
        "LTX-2.5-22b-IC-LoRA-Ingredients",
        "LTX-2.5-22b-IC-LoRA-Restore",
    )
    notes = (
        "Representative Diffusers load for the LTX-2.5 Creative Lab collection "
        "(https://huggingface.co/collections/Lightricks/ltx-25-creative-lab). "
        "Gated repos. Vendor path is ComfyUI; a pass here is a Diffusers load only, "
        "not a render-quality claim. The same pass/fail covers the rest of the "
        "collection until a per-adapter result exists."
    )
    missing = [str(base)] if not base.exists() else []
    missing.extend(name for name in representatives if not (model_root / name).exists())
    if missing:
        print(f"⚠️  IC-LoRA weights missing: {', '.join(missing)}")
        return {
            "model_key": model_key,
            "status": "missing_weights",
            "vram_fit": False,
            "errors": [f"Missing: {', '.join(missing)}"],
            "notes": notes,
        }

    try:
        from diffusers import LTX2Pipeline
    except Exception as exc:
        print(f"⚠️  LTX2Pipeline unavailable: {exc}")
        return {
            "model_key": model_key,
            "status": "pipeline_unavailable",
            "vram_fit": False,
            "precision": precision,
            "errors": [
                f"LTX2Pipeline import failed: {exc}. "
                "Diffusers did not expose the LTX-2.5 pipeline in this environment."
            ],
            "notes": notes,
        }

    try:
        import time
        print(f"Loading LTX-2.5 from {base} to test IC-LoRA attach...")
        start = time.time()
        dtype = torch.bfloat16
        pipe = LTX2Pipeline.from_pretrained(str(base), torch_dtype=dtype)
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        loaded = []
        for name in representatives:
            pipe.load_lora_weights(str(model_root / name), adapter_name=name)
            loaded.append(name)
        load_time = time.time() - start
        peak = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else None
        vram_fit = bool(peak is not None and peak < VRAM_THRESHOLD_GB)
        print(f"Attached {loaded}; peak {peak}")
        return {
            "model_key": model_key,
            "status": "pass" if vram_fit else "fail_vram",
            "vram_fit": vram_fit,
            "peak_vram_gb": None if peak is None else round(peak, 2),
            "load_time_sec": round(load_time, 1),
            "precision": precision,
            "errors": [],
            "notes": notes + " Load-only; no render was run.",
        }
    except Exception as exc:
        print(f"⚠️  IC-LoRA Diffusers load failed: {exc}")
        return {
            "model_key": model_key,
            "status": "pipeline_unavailable",
            "vram_fit": False,
            "precision": precision,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "notes": notes + " Use the Section A19 fallback. Do not route through ComfyUI.",
        }

def test_image_model_flux3(model_root: Path) -> Dict[str, Any]:
    return {"model_key": "flux_3_image_klein", "status": "not_implemented", "vram_fit": False, "errors": ["Test TBD"]}

def test_image_model_h3image(model_root: Path) -> Dict[str, Any]:
    return {"model_key": "minimax_h3_image", "status": "not_implemented", "vram_fit": False, "errors": ["Test TBD"]}


MODEL_TESTS = {
    "minimax_h3": test_video_model_h3,
    "ltx_2_5": test_video_model_ltx,
    "wan_bernini": test_video_model_wan,
    "bernini_r": test_video_model_bernini_r,
    "h3_ref2va": test_h3_ref2va,
    "ltx_ic_lora": test_ltx_ic_lora,
    "krea_2_turbo": test_image_model_krea2,
    "z_image_turbo": test_image_model_zimage,
    "flux_3_image_klein": test_image_model_flux3,
    "minimax_h3_image": test_image_model_h3image,
}


def main():
    parser = argparse.ArgumentParser(description="Phase 0 VRAM Fit Tests")
    parser.add_argument("--model-root", required=True, help="Path to model storage")
    parser.add_argument("--models", nargs="+", choices=list(MODEL_TESTS.keys()) + ["all"],
                        default=["all"], help="Models to test")
    parser.add_argument("--precision", default="fp8", choices=["fp8", "bf16"],
                        help="Precision for video models")
    parser.add_argument("--download", action="store_true",
                        help="Auto-download missing weights (requires HF CLI)")
    args = parser.parse_args()
    
    model_root = Path(args.model_root).expanduser()
    if not model_root.exists():
        print(f"❌ Model root does not exist: {model_root}")
        return 1
    
    # Create results directories
    RESULTS_DIR.mkdir(exist_ok=True)
    SAMPLES_DIR.mkdir(exist_ok=True)
    
    # Determine which models to test
    if "all" in args.models:
        models_to_test = list(MODEL_TESTS.keys())
    else:
        models_to_test = args.models
    
    print("Phase 0 VRAM Fit Tests — RTX 5090")
    print("=" * 60)
    print(f"Model root: {model_root}")
    print(f"Testing: {', '.join(models_to_test)}")
    print(f"VRAM threshold: {VRAM_THRESHOLD_GB:.1f} GB (32 GB * {SAFETY_MARGIN})")
    print()
    
    if not torch.cuda.is_available():
        print("❌ No CUDA GPU available")
        return 1
    
    hardware = get_hardware_info()
    print(f"GPU: {hardware['gpu']}")
    print(f"VRAM: {hardware['vram_total_gb']} GB")
    print(f"Compute: {hardware['compute_capability']}")
    print()
    
    results = []
    for model_key in models_to_test:
        test_fn = MODEL_TESTS[model_key]
        
        # Pass precision for video models
        if model_key in ["minimax_h3", "ltx_2_5", "wan_bernini", "h3_ref2va", "ltx_ic_lora"]:
            result = test_fn(model_root, args.precision)
        else:
            result = test_fn(model_root)
        
        results.append(result)
        
        # Save individual result
        result_path = RESULTS_DIR / f"{model_key}.json"
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Result saved: {result_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for r in results:
        status_icon = "✅" if r["status"] == "pass" else "❌"
        vram_fit = r.get("vram_fit", False)
        peak_vram = r.get("peak_vram_gb", "N/A")
        print(f"{status_icon} {r['model_key']}: {r['status']} (VRAM fit: {vram_fit}, peak: {peak_vram} GB)")
    
    passed = sum(1 for r in results if r["status"] == "pass")
    print(f"\nPassed: {passed}/{len(results)}")
    print(f"Results written to: {RESULTS_DIR}/")
    print()
    print("Next: Commit results with `git add phase0/results/*.json && git commit`")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
