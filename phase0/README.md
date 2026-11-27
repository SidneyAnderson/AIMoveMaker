# Phase 0 GPU Test Kit — RTX 5090 32 GB

**Purpose:** Measure VRAM fit, load times, and performance for Movie Maker models on your local RTX 5090 PC.

**Hardware target:**
- Windows 11 PC, RTX 5090 32 GB (sm_120)
- Intel Core Ultra 9 285K
- CUDA 12.8+
- WSL Ubuntu-22.04 (optional, for Linux test path)
- Model storage: `D:\AIModels\` (Windows) or `~/AIModels/` (WSL)

**Output:** JSON results in `phase0/results/*.json` that the coding agent will read to populate `ModelRegistry.fits_target_vram` and other flags.

---

## Quick Start (Choose Your Platform)

### Option A: Native Windows (PowerShell)

```powershell
# 1. Create isolated Python environment
cd phase0
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install diffusers>=0.43 transformers accelerate safetensors omegaconf
pip install redis psutil

# 3. Check environment
python env_check.py --model-root D:\AIModels

# 4. Run all tests (downloads missing weights, skips what's unavailable)
.\run_all.ps1 -ModelRoot "D:\AIModels"
```

### Option B: WSL Ubuntu-22.04

```bash
# 1. Create isolated Python environment
cd phase0
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install diffusers>=0.43 transformers accelerate safetensors omegaconf
pip install redis psutil

# 3. Check environment
python env_check.py --model-root ~/AIModels

# 4. Run all tests
./run_all.sh --model-root ~/AIModels
```

---

## Expected Runtime

| Test | Models | Time (estimate) | VRAM Peak |
|------|--------|----------------|-----------|
| env_check.py | (none) | 10 seconds | <1 GB |
| vram_fit.py | 7 models + 1 LoRA | 20-40 minutes | 10-30 GB per model |
| converter_check.py | H3 (stub) | 5 minutes | TBD |

**Total:** ~45 minutes if all weights are pre-downloaded, 2-4 hours including downloads.

---

## What Gets Tested

### Video Models (3 families)

1. **MiniMax H3** (`minimax_h3`)
   - Hugging Face: `MiniMaxAI/MiniMax-H3`
   - Test: Load DiT + text encoder + VAE, render 22-frame 1024×576 test clip
   - Also test: H3 + 1 LoRA loaded
   - Precision: FP8 (torchao) or NVFP4 (ModelOpt) if `sm_120` supports; else BF16

2. **LTX-2.5** (`ltx_2_5`)
   - Hugging Face: `Lightricks/LTX-Video-2.5` (or the official LTX-2.5 path)
   - Test: Load via `LTX2Pipeline` or `LTX25AutoBlocks`, render 24-frame 768×512 clip
   - Precision: FP8 or BF16

3. **Wan 2.2 + Wan Animate 2** (`wan_bernini`)
   - Hugging Face: TBD (Wan 2.2 official path; Wan Animate 2 via `WanAnimate2Pipeline`)
   - Test: Load, render 16-frame 512×512 clip
   - Precision: BF16 or FP8

### Image Models (4 shipped defaults)

4. **Krea 2 Turbo** (`krea_2_turbo`)
   - Hugging Face: `krea/Krea-2-Turbo` (gated; needs HF token)
   - Test: Load via `Krea2Pipeline`, render 1024×1024 still (8 steps, CFG off)

5. **Z-Image-Turbo** (`z_image_turbo`)
   - Hugging Face: `Tongyi-MAI/Z-Image-Turbo`
   - Test: Load via `ZImagePipeline`, render 1024×1024 still (9 steps)

6. **FLUX 3 Image Klein** (`flux_3_image_klein`)
   - Hugging Face: `black-forest-labs/flux-3-image-klein`
   - Test: Load via `Flux3DistilledModularPipeline`, render 1024×1024 still (16 steps)
   - **Also test:** With 9B prompt upsampler offloaded (measure separately)

7. **MiniMax-H3-Image** (`minimax_h3_image`)
   - Hugging Face: `MiniMaxAI/MiniMax-H3-Image`
   - Test: Load via `MiniMaxH3ImageModularPipeline`, render 16:9 still (try 1920×1080 first)
   - **Gate:** Official BF16 + full text encoder won't fit; test community quantization if available

---

## Model Download (Pre-Test)

**All models require Hugging Face CLI:**
```bash
pip install huggingface-hub
huggingface-cli login  # Paste your HF token (required for gated Krea 2 Raw)
```

**Video models:**
```bash
huggingface-cli download MiniMaxAI/MiniMax-H3 --local-dir D:\AIModels\MiniMax-H3
huggingface-cli download Lightricks/LTX-Video-2.5 --local-dir D:\AIModels\LTX-2.5
# Wan 2.2 path TBD
```

**Image models:**
```bash
huggingface-cli download krea/Krea-2-Turbo --local-dir D:\AIModels\Krea-2-Turbo
huggingface-cli download Tongyi-MAI/Z-Image-Turbo --local-dir D:\AIModels\Z-Image-Turbo
huggingface-cli download black-forest-labs/flux-3-image-klein --local-dir D:\AIModels\flux-3-image-klein
huggingface-cli download MiniMaxAI/MiniMax-H3-Image --local-dir D:\AIModels\MiniMax-H3-Image
```

**Note:** `vram_fit.py --download` will attempt downloads if `--model-root` is set and weights are missing.

---

## Results Output

Each test produces:
- `phase0/results/<model_key>.json` — Structured results (see `schema.json`)
- `phase0/results/samples/<model_key>_sample.png` or `.mp4` — Visual output (gitignored)

**Example `minimax_h3.json`:**
```json
{
  "model_key": "minimax_h3",
  "test_date": "2026-11-27T20:30:00Z",
  "hardware": {
    "gpu": "NVIDIA GeForce RTX 5090",
    "vram_total_gb": 32,
    "cuda_version": "12.8",
    "compute_capability": "sm_120"
  },
  "precision": "fp8",
  "vram_fit": true,
  "peak_vram_gb": 28.3,
  "load_time_sec": 45.2,
  "inference_time_sec": 12.1,
  "it_per_sec": 1.82,
  "output_resolution": "1024x576x22",
  "status": "pass",
  "errors": [],
  "notes": "With 1 LoRA loaded (character adapter, 150 MB)"
}
```

**When a model fails or is missing:**
```json
{
  "model_key": "wan_bernini",
  "status": "missing_weights",
  "vram_fit": false,
  "errors": ["Weights not found at D:\\AIModels\\Wan-2.2"]
}
```

---

## Submitting Results

After tests complete:

```bash
# Verify results exist
ls phase0/results/*.json

# Commit results (samples are gitignored)
git add phase0/results/*.json
git commit -m "phase0: RTX 5090 VRAM fit results"
git push origin <your-branch>
```

**Or paste JSON into a PR comment** if you prefer not to commit.

The coding agent will read these results and populate:
- `ModelRegistry.fits_target_vram` (true if `peak_vram_gb < 32 * 0.9`)
- `ModelRegistry.peak_vram_gb`
- `ModelRegistry.load_time_sec`
- `ModelRegistry.is_active` (true if status=pass)

---

## Troubleshooting

### "CUDA out of memory"
- Close other GPU applications
- Try lower precision (FP8 instead of BF16)
- Reduce test resolution in `vram_fit.py --resolution`

### "Weights not found"
- Check `--model-root` path
- Run `huggingface-cli download <model>` manually
- Or use `vram_fit.py --download` to auto-fetch

### "Redis connection failed" (env_check.py)
- Not required for Phase 0 GPU tests
- Redis is only needed for the full app (Celery queues)

### Gated model access denied (Krea 2 Raw)
- Accept license at https://huggingface.co/krea/Krea-2-Raw
- Run `huggingface-cli login` with valid token

### SGLang installation issues
- SGLang is **optional** for Phase 0
- Video tests use Diffusers pipelines by default
- If SGLang fails to install, skip it (`--no-sglang`)

---

## Safety Notes

- **10% VRAM margin:** Models must stay under 28.8 GB peak to pass (32 GB * 0.9)
- **Test clips are SHORT:** 16-24 frames, low resolution (512p-1080p)
- **Full production renders** will be longer and may hit VRAM ceilings not caught here
- **Always monitor:** Use `nvidia-smi` or Task Manager GPU view during tests

---

## Questions?

If a test fails or you encounter hardware/driver issues:
- Capture the full error output
- Include `nvidia-smi` output
- Note your CUDA/driver versions
- Report in the PR or issue tracker

The coding agent will adapt the registry seed based on your actual results, so **accurate measurements matter**.

---

**Start command (Windows):**
```powershell
cd phase0
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install diffusers>=0.43 transformers accelerate safetensors redis psutil
python env_check.py --model-root D:\AIModels
.\run_all.ps1 -ModelRoot "D:\AIModels"
```

**Start command (WSL Ubuntu):**
```bash
cd phase0
python3 -m venv .venv && source .venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install diffusers>=0.43 transformers accelerate safetensors redis psutil
python env_check.py --model-root ~/AIModels
./run_all.sh --model-root ~/AIModels
```
