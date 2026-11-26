# Bringing Long-Video-Creator into AIMoveMaker

**Gap Analysis & Phased Plan**

**Version:** Updated 2026-11-26  
**Estimate:** 41–58 days across Phases 0–5  
**Summary:** Code-verified multi-user gap analysis updated for Sidney's 2026-11-25 decisions: Redis/Celery/RBAC retained as foundation, runtime-agnostic standard weights, Import Model convert+quantize pipeline with safety gate, and Seed Hunter v3.

---

## Table of Contents

1. [Summary Verdict](#summary-verdict)
2. [Project-Level Core Model](#project-level-core-model)
3. [Import Model & Model Library](#import-model--model-library)
4. [MiniMax H3 + LoRA](#minimax-h3--lora)
5. [Seed Hunter v3 Workflow & Walkthrough Mapping](#seed-hunter-v3-workflow--walkthrough-mapping)
6. [Feature Gap Matrix](#feature-gap-matrix)
7. [Gap and Effort Breakdown](#gap-and-effort-breakdown)
8. [Design Conflicts](#design-conflicts)
9. [Key Risks and Unknowns](#key-risks-and-unknowns)
10. [Recommended Phased Build Order](#recommended-phased-build-order)

---

## Summary Verdict

**Multi-user foundation kept (Redis, Celery, RBAC); Import Model & per-engine GPU routing bring total to 41–58 days**

Keeping AIMoveMaker's Redis, Celery priority queues, Redis pub/sub WebSockets, JWT/OAuth auth, and Creative/Engineer RBAC saves ~3–4 days in Phase 1 compared to rewriting a single-user local queue. Adding multi-user model/LoRA visibility, Import/delete permissions with shared-folder reference checks, admin-vs-user secret scoping, Celery GPU-worker routing per engine venv, and Docker-free native Redis installation (Ubuntu `redis-server`, Windows Memurai/native Redis) adjusts the estimate from 39–56 days to 41–58 days across Phases 0–5.

Phase 0 proves both MiniMax H3 + one LoRA on the RTX 5090 and the pruned-ComfyUI-to-standard converter + quantizer round-trip. Phase 2 delivers the RBAC-guarded Import Model pipeline right after Phase 1 establishes the project model lock and multi-user recursive library.

### Key Metrics

- **24** audited feature areas (LVC + Seed Hunter v3 + Import Model)
- **0 / 10 / 14** (Has / Partial / Missing)
- **41–58d** revised build effort (Net +2d vs 39–56d for multi-user + native Redis)
- **Phase 0 + 2** converter & Import gates (Round-trip spike in P0; full Importer in P2)

---

## Project-Level Core Model

Every project is locked to a single core video model family chosen at creation time, preventing mixed-model timelines (for example, mixing MiniMax H3 and Wan segments inside one project).

### Schema and UI

| Component | Description |
|-----------|-------------|
| **Schema anchor** | `Project.core_video_model` + `Project.workflow_profile_id` set on creation; immutable in place (migration requires cloning into a new project). |
| **Profile-driven UI** | Selected `WorkflowProfile` dictates modes (`t2va`/`fl2va`/`ref2va` vs `t2v`/`i2v`/`v2v`), resolution/MP presets, `17n+5` frame limits, FPS, and dual schedulers. |
| **Scoped LoRA library** | `LoRARegistry` filters strictly to `Project.core_video_model`, partition (`fl2va` vs `ref2va`), and recorded `lora_compatibility_notes`. |
| **Uniform continuity** | Overlap conditioning, frame/latent caches, Save/Load Job signatures, and timeline assembly only ever process one model family per project. |

### Simplifications

- **Dropped:** Per-segment model selector & mixed-model assembly
  - Remove `VideoClip.model_id` / `Keyframe.model_id` per-shot engine switching and cross-model FPS/color/latent reconciliation during FFmpeg assembly.
  - Status: **Eliminated**

- **Dropped:** In-place model switch migration preview (PROFILE-07)
  - No mid-project engine swapping inside an open timeline; switching core models means cloning the project/storyboard to a new project.
  - Status: **Eliminated**

- **Simplified:** Output policy, continuity & Save/Load Job checks
  - Validate `(mode, resolution, frames, fps)` against one project profile; continuity lineage (`CONT-01–08`) and job restore (`JOB-01–08`) assume uniform VAE/latent geometry.
  - Status: **~7–10d saved**

---

## Import Model & Model Library

**Settled 2026-11-25 design:** Normalize ComfyUI/Civitai artifacts into standard unpruned+quantized Diffusers/SGLang assets with a mandatory render safety gate before original cleanup.

### Import Model Pipeline

```
Civitai download     Header detect      Convert & quantize    Safety gate       Keep or delete
or local file   →    (Standard vs   →   Split QKV, expand  →  Test-load +   →  User chooses delete
                     ComfyUI/LoRA)      AdaLN → FP8/NVFP4     sample render     or move folder
```

### Pipeline Steps

1. **Civitai download or local file intake**
   - Accepts a Civitai model/version URL or local `.safetensors` path (replacing the stubbed Civitai endpoints in `backend/routers/integrations.py`) and captures source metadata and author compatibility notes.

2. **Safetensors header layout detection**
   - Reads header JSON before loading weights into VRAM: distinguishes standard unpruned Diffusers models from ComfyUI-packed/pruned models (e.g., `adaln_basis`, `adaln_t_table`, fused `attn.qkv_proj`, `comfy_quant`/`weight_scale`) and ComfyUI/Kohya LoRAs.

3. **Convert to standard layout + quantize in one pass**
   - Renames keys to standard Diffusers layout, splits fused `attn.qkv_proj` into separate Q/K/V projections, expands pruned AdaLN (`adaln_basis`/`adaln_mean`/`adaln_t_table` + per-block `adaln_proj`) into full per-block AdaLN, converts ComfyUI/Kohya LoRA keys, and quantizes to FP8 or NVFP4 (`torchao` `TorchAoConfig` for Diffusers, NVIDIA ModelOpt for SGLang).

4. **Mandatory test-load & sample render safety gate**
   - Loads the newly written converted/quantized artifact into the target non-ComfyUI runtime (Diffusers or SGLang) and executes a short sample render. If loading or rendering fails, the original file is never touched.

5. **RBAC-checked cleanup prompt & library registration**
   - Only after the safety gate passes—and only when the user is an Admin or the unreferenced uploader (`owner_id`)—does the UI prompt to delete the original or move it to an archive folder. The library entry records `visibility` (`global`/`user`), `base_model`, and `lora_compatibility_notes`.

### Evidence and Notes

- **Civitai 'H3 Eros Max' v1.0 BF16 header (534 tensors)**
  - Inspected at `/workspace/10Eros_Max_8stepTurbo_v1.0_hybrid.safetensors.header.json`: 50 blocks (`blocks.0..49`), hidden `5376`, fused `attn.qkv_proj.weight` `[21504, 5376]`, `adaln_basis` `[8, 2688]`, `adaln_mean` `[2688]`, `adaln_t_table` `[1025, 8]`, per-block `adaln_proj.linear.weight` `[96768, 8]`, and metadata `"converted_from": "diffusers MiniMax-H3 transformer"`.
  - Status: **Verified header**

- **Civitai 'H3 Eros Max' v1.0 int8_HQ header (894 tensors)**
  - Inspected at `/workspace/10Eros_Max_8stepTurbo_v1.0_hybrid-int8_HQ.safetensors.header.json`: uses `"h3_native_hq.topology": "bf16_edges_int8_interiors"` (blocks 0 & 49 BF16; interior blocks `I8` with ComfyUI `comfy_quant` `U8 [82]` and `weight_scale` `F32 [rows, 1]`, `convrot: true, convrot_groupsize: 256, int8_tensorwise`). Importer flags pre-quantized ComfyUI ConvRot files and prefers converting from the BF16 file.
  - Status: **ComfyUI-specific**

- **Fine-tune LoRA sensitivity stored on library entry**
  - The `10Eros_Max` author warns that base H3 LoRAs hit ~2x harder on this fine-tune, so it requires low-rank MLP-only LoRAs. Recording `base_model` and `lora_compatibility_notes` per library entry surfaces this warning automatically when building a LoRA stack.
  - Status: **Library metadata**

- **Model library**
  - Multi-user recursive folder scan & pre-render missing-piece check: The app scans shared and user-chosen model folders recursively (`LIB-01–08`, budgeted in Phase 1—no double-count), tracks `global` vs `user` visibility, and blocks render start if required companions (text encoder, video VAE, audio VAE, or latent upscaler) are missing.
  - Status: **Pre-render check**

---

## MiniMax H3 + LoRA

**Runtime, formats, and unknowns**

Updated for the runtime-agnostic policy: prefer standard unpruned Diffusers/SGLang weights and convert ComfyUI artifacts at import time.

### Inference & Layout Policy

- **Runtime-agnostic outside ComfyUI; ComfyUI compatibility not a goal**
  - Base models and LoRAs load strictly through Diffusers (`diffusers>=0.40.0` `MiniMaxH3ModularPipeline`) or SGLang (`>=0.5.17`), never ComfyUI. Instead of maintaining ComfyUI ConvRot/pruned kernels at inference time, `Import Model` normalizes ComfyUI weights into standard Diffusers layout once.
  - Status: **Settled rule**

- **Architecture: packed omni-modal sequence + dual DiT partitions**
  - MiniMax-H3 (33B full) denoises one packed sequence of text, media refs, video latents, and 32 kHz stereo audio latents in one forward pass (guidance-distilled, no CFG) using two schedulers (`shift=12.0` video, `shift=3.0` audio). Two partitions share Qwen3-VL 32B and VAEs: `transformer/` (`t2va`/`fl2va`) and `transformer_ref/` (`ref2va`).
  - Status: **Diffusers Docs**

- **Primary Runtime A: Hugging Face diffusers (>= 0.40.0)**
  - Merged into `diffusers` `main` (PR #14355 & #14408, Aug 2026) as `ModularPipeline.from_pretrained('MiniMaxAI/MiniMax-H3', workflow='ref2va')` with `TorchAoConfig` FP8/INT8 quantization and `MiniMaxH3LoraLoaderMixin`.
  - Status: **First-class LoRA API**

- **Primary Runtime B: SGLang Diffusion (>= 0.5.17) + NVIDIA ModelOpt**
  - High-throughput serving path (`docs.sglang.io/cookbook/diffusion/MiniMax/MiniMax-H3`) supporting standard unpruned weights, layerwise offload (~18 GB peak on 4090), and NVIDIA ModelOpt FP8/NVFP4 quantization on Blackwell (`sm_120`).
  - Status: **Serving / NVFP4 path**

### Quantization & Weights

- **Prefer standard unpruned Diffusers weights, quantized at import to FP8 or NVFP4**
  - Start from unpruned Diffusers BF16/FP16 checkpoints—or convert ComfyUI BF16 checkpoints like `10Eros_Max_8stepTurbo_v1.0_hybrid.safetensors` (`534` tensors)—and quantize in the same import step via `torchao` (`TorchAoConfig` for Diffusers) or NVIDIA ModelOpt (for SGLang).
  - Status: **Preferred target**

- **Legacy A:\\AIModelsProd & ComfyUI-specific formats**
  - `MODEL_AUDIT.md` lists Comfy-Org `*_pruned_int8_convrot.safetensors` and `*_nvfp4.safetensors`, and `10Eros_Max` `int8_HQ` uses ComfyUI `comfy_quant`/`weight_scale` + `convrot_groupsize: 256`. Under the new rule, BF16 sources convert cleanly; pre-quantized ComfyUI `comfy_quant` files require dequantize+convert or fetching the BF16 counterpart.
  - Status: **Legacy / import source**

- **Companion artifacts required by recursive preflight**
  - Standard H3 generation needs `Qwen3-VL 32B` (`nvfp4_awq` or `torchao`/ModelOpt quantized), `minimax_h3_video_vae_fp16.safetensors` (or compatible VAE), `minimax_h3_audio_vae_fp32.safetensors`, and `minimax_h3_latent_upscaler_3d_bf16.safetensors` for Stage 2.
  - Status: **Preflight checked**

### LoRA Training & Loading

- **Training ecosystem & Diffusers MiniMaxH3LoraLoaderMixin**
  - `ostris/ai-toolkit`, `DiffSynth-Studio`, `unsloth`, and `fal` train H3 LoRAs. Diffusers PR #14408 (`MiniMaxH3LoraLoaderMixin`) loads PEFT, `ai-toolkit` (`diffusion_model.` fused QKV/SwiGLU), `DiffSynth-Studio`, and Turbo LoRAs (`larryvrh`, `InstantX`, `lightx2v`) with partition routing (`load_into_transformer_ref=True`) and recommends unfused runtime application.
  - Status: **Diffusers 0.40+**

- **Pruned AdaLN & ComfyUI/Kohya LoRA conversion at import**
  - Because base checkpoints are expanded to standard unpruned Diffusers layout during Import Model, LoRAs trained against unpruned bases load directly; ComfyUI/Kohya LoRA files are key-converted at import, and any LoRA trained specifically against pruned AdaLN weights is flagged or skipped on AdaLN layers during conversion.
  - Status: **Normalized at import**

- **Fine-tune sensitivity & Stage 1 vs Continuation LoRA rules**
  - `10Eros_Max` requires low-rank MLP-only LoRAs (base H3 LoRAs hit ~2x harder), tracked in `lora_compatibility_notes`. Seed Hunter v3 uses separate Stage 1+2 (`Turbo` + `Realism`), Upscale-only, and Vocal LoRA slots, disabling Turbo LoRAs during 10–14 step continuations.
  - Status: **UI + preflight rule**

### Knowns vs Unknowns

- **Unknown #1 (P0 gate): Pruned AdaLN reconstruction math from adaln_basis/t_table**
  - Headers show `adaln_basis [8, 2688]`, `adaln_mean [2688]`, `adaln_t_table [1025, 8]`, and per-block `adaln_proj.linear.weight [96768, 8]`. Phase 0 must prove the exact algebraic/linear reconstruction into standard Diffusers per-block AdaLN weights passes a short sample render.
  - Status: **Prove in Phase 0**

- **Unknown #2 (P0 gate): TorchAO vs NVIDIA ModelOpt FP8/NVFP4 + LoRA stacking on RTX 5090**
  - Need to benchmark whether `diffusers` `TorchAoConfig` (FP8/INT8) or `SGLang` + ModelOpt (FP8/NVFP4) better supports unfused dynamic LoRA loading + `Qwen3-VL` offload inside 32 GB VRAM on `sm_120`.
  - Status: **Prove in Phase 0**

- **Unknown #3: Dequantizing ComfyUI ConvRot int8_HQ checkpoints vs requiring BF16**
  - `10Eros_Max` `int8_HQ` has `I8` rotated weights + `U8` `comfy_quant` + `F32` `weight_scale`. Phase 0/2 should decide whether the converter supports Hadamard un-rotation for `int8_HQ` or requires importing from the BF16 source file before quantizing.
  - Status: **Medium unknown**

- **Unknown #4: H3 RefMods & 3D latent upscaler outside ComfyUI**
  - `ComfyUI-MiniMaxH3Mod` (`RefMods`) and `LBH-123-AI/Minimax_h3_latent_Upscaler` currently ship as ComfyUI nodes; standalone Diffusers/PyTorch wrappers must be ported in Phase 3/4.
  - Status: **Medium-High unknown**

### References

- [Diffusers MiniMax-H3 Pipeline Docs](https://huggingface.co/docs/diffusers/api/pipelines/minimax_h3)
- [Diffusers PR #14408: MiniMaxH3LoraLoaderMixin](https://github.com/huggingface/diffusers/pull/14408)
- [SGLang Diffusion MiniMax-H3 Cookbook](https://docs.sglang.io/cookbook/diffusion/MiniMax/MiniMax-H3)
- [Diffusers TorchAoConfig Quantization](https://huggingface.co/docs/diffusers/quantization/torchao)
- [AtlasCloudAI/awesome-minimax-h3 (Ecosystem Index)](https://github.com/AtlasCloudAI/awesome-minimax-h3)

---

## Seed Hunter v3 Workflow & Walkthrough Mapping

Parsed from Seed Hunter v3.0 ComfyUI JSON (168 nodes, 6 subgraphs, 36 Pixaroma groups, 254 links) and Fox•Fur•Essence Films walkthrough (lKmv63AKBhY, 915s).

The Seed Hunter v3.0 workflow and walkthrough define the practical H3 creative loop. Each row explicitly states whether the requirement came from the workflow JSON, the video transcript, or engineering inference.

### Pipeline Stages

| Stage | Source | What Seed Hunter v3 Does | AIMoveMaker Status | Mapping onto AIMoveMaker |
|-------|--------|--------------------------|-------------------|-------------------------|
| **1. Structured H3 Prompt IDE & RefMods** | Workflow JSON | Dual `H3PromptIDE` buffers, 6-section `Singularity` schema (`subject_definitions`, `summary`, `retention_analysis`, `detailed_description` with `[Shot N]`/`<d>[English]` tags, `overall_soundscape`, `non_diegetic_music`), `MiniMaxH3MediaLoader`/`ReferenceSplitter`, and `MiniMaxH3RefModsLoader`/`Apply`. | Missing | AIMoveMaker `PromptTemplate` is flat text. Must add structured H3 prompt schema editor, secondary scratch buffer, ordered `<Subject>/<Picture>/<Audio>` slots, and RefMod weight/attention controls. |
| **2. Model, LoRA & Attention Optimization** | Workflow JSON + Transcript | `Load Models & Patches` (`minimax_h3_fl2va_pruned_int8_convrot`, `qwen3vl_32b_minimax_h3_nvfp4_awq`, Kijai `int8_convrot` video VAE, `audio_vae_fp32`), 3 `PixaromaLoraLoader` slots (Stage 1+2 Turbo Dareties @ 0.75 + Realism LoRA, Upscale-only LoRA, Vocal LoRA), `MiniMaxChunkFeedForward`, `MiniMaxLowVRAMAttention`, `MiniMaxH3SigmaShift` (12/6 or 12/3), `BlockSparseAttention` (`SLA`/`Sol-Attn`/`VSA`), and `taeh3` live preview. | Partial | `hardware_profile.py` detects RTX 5090 (`sm_120`). Under the new runtime-agnostic rule, AIMoveMaker converts ComfyUI-packed models/LoRAs on import rather than executing ComfyUI ConvRot formats natively, while preserving the 3 LoRA slots and dual sigma shifts. |
| **3. Mode & Conditioning Router** | Workflow JSON + Transcript | `Options Control Panel` toggles Normal `ref2va` vs Seamless Video Continuation vs Dialogue/Voice Cloner, `<Picture 1>` first frame / `<Picture 2>` last frame (`MiniMaxH3AddGuide`), `Force <Audio 1> into Latent` (`VAEEncodeAudio` + `LTXVSeparateAVLatent` + `SetLatentNoiseMask`), and `OG Video Has No Audio` silence pad. | Missing | `VideoClip.mode` only has `t2v`/`i2v`/`v2v` (with `v2v` falling back to `i2v` in `video.py`). Needs `ref2va`, `fl2va` frame pins, continuation mode, and audio latent-locking. |
| **4. Voice Cloner / Dialogue Pre-Gen** | Workflow JSON + Transcript | Dedicated `Dialogue / Audio Genner` branch generating 3 audio takes (`Audio #1–#3`) from `<Audio 1>` or 15–45s vocal upload, `*word*` emphasis, scene-context delivery prompt, and length tuning; creator pads pauses in Audacity and feeds back via Forced Audio. | Missing | `audio.py` has Coqui TTS & MusicGen, not H3 timbre-cloned dialogue pre-gen or built-in silence/pause padding before feeding back into video latent-lock. |
| **5. Stage 1 Multi-Seed Previews** | Workflow JSON + Transcript | `easy seed` fans out to 3 samplers (`a`, `a+1000`, `a+2000`) at `0.2–0.4 MP`, `17n+5` frames (`24 fps`), `er_sde`/`beta` or `ManualSigmas`, decoding 3 video+audio previews (`#1–#3`); Single Pass runs `1.0–2.0 MP` directly. | Partial | `Keyframe.candidate_asset_ids` handles image multi-takes, but `VideoClip` tracks one output and lacks 3-seed preview generation, `17n+5` frame snapping, and promote-to-stage-2. |
| **6. Stage 2 Latent Upscale & Reroll** | Workflow JSON | Select winning preview `#1/#2/#3`, run `MiniMaxH3LatentUpscaleWithModel` (`minimax_h3_latent_upscaler_3d_bf16.safetensors`) to target `ResolutionSelector`, re-denoise (`linear_quadratic`, 2–6 steps) with cached Stage 1, independent reroll seed, optional Upscale LoRA, and First/Last frame PNG export. | Missing | AIMoveMaker deferred spatial upscaling to v2 (`image.py`) and has no two-stage latent upscaler, Stage-1 cache reuse, or first/last frame extraction hooks. |
| **7. Seamless Continuation & Quality Reset** | Workflow JSON + Transcript | Trim OG clip + audio to last `5 / 22 / 39 / 56` (`17n+5`) overlap frames, turn Turbo LoRA OFF (10–14 steps), blend overlap & stitch (`ImageBatchMulti` + `AudioConcat`). Every ~3 extensions, apply (a) camera-away redraw from `<Subject>` sheet or (b) 1080p image-upscaled still pinned as `<Picture 2>` last frame. | Missing | AIMoveMaker has no video/audio overlap conditioning, no extension drift counter, no pinned-keyframe still-upscale hook, and no redraw/reset continuity workflow. |
| **8. Cadence, RIFE & NLE Seam Finishing** | Workflow JSON + Transcript + Inferred | `AnimeCadence` 2D frame limiter + `RIFEInterpolation` (24->48/60 fps) + `VHS_VideoCombine` H.264/MP4 (JSON). Creator then fixes H3's 5-frame overlap lighting/contrast/warmth shift in DaVinci Resolve color tab and masks seams with compound-clip Gaussian/CineFocus blur + micro zoom/glow (Transcript). | Partial | Has `RIFEInterpolation` (`interpolation.py`) and FFmpeg export (`generation_tasks.py`). Missing `AnimeCadence`, adjacent-frame A/B seam color/exposure grading (`TimelineView.tsx`), and compound blur+zoom transition filters (Inferred NLE scope). |

---

## Feature Gap Matrix

Updated for runtime-agnostic standard weights, Import Model convert+quantize+gate, recursive library preflight, and Seed Hunter v3; effort values are engineering estimates.

| Feature Area | Spec / Source | Status | What Must Change in AIMoveMaker | Rule Impact | Est. Effort |
|-------------|---------------|--------|----------------------------------|-------------|-------------|
| **Project-level core model & WorkflowProfile** | PROFILE-01–08, Core Model Rule | Missing | Add immutable `Project.core_video_model` + `workflow_profile_id` at creation; drop per-segment model selectors (`VideoClip.model_id` / `Keyframe.model_id`) and cross-model switching inside active timelines; clone-to-migrate only. | Simplified (dropped per-clip switching & mixed assembly) | M (3–4d est.) |
| **Runtime-agnostic H3 engine (Diffusers / SGLang)** | GEN-01–03, Runtime-Agnostic Rule | Missing | Run MiniMax H3 outside ComfyUI via standard unpruned Diffusers (`diffusers>=0.40` `MiniMaxH3ModularPipeline` + `TorchAO`) or SGLang (`>=0.5.17` + ModelOpt) as Celery GPU workers in `.venvs/h3`; ComfyUI compatibility explicitly dropped. | Standard layout only (-2 to -3d); +1d for Celery per-engine GPU queue routing | L (7–10d est.) |
| **Import Model: intake, layout detect & Civitai** | Import Model Decision (2026-11-25) | Partial | Replace Civitai search/download stubs (`integrations.py`) with Civitai URL/ID + local file intake, safetensors header parser (`10Eros_Max` / standard / LoRA), RBAC-guarded delete-vs-keep-and-move prompt (checking shared-folder references), and `base_model` + `lora_compatibility_notes`. | New delta (+3–4d est. incl. multi-user Import/delete permissions) | M (3–4d est.) |
| **ComfyUI -> Diffusers checkpoint & LoRA converter** | Import Model Decision, 10Eros_Max headers | Missing | Convert ComfyUI-packed H3 weights to standard Diffusers format: rename keys, split fused `attn.qkv_proj` (`[21504, 5376]`) into Q/K/V, expand pruned AdaLN (`adaln_basis`/`adaln_mean`/`adaln_t_table` -> full per-block AdaLN), and convert ComfyUI/Kohya LoRA keys. | New delta (+3–4d est.); resolves pruned-AdaLN mismatch at import time | M (3–4d est.) |
| **Inline FP8 / NVFP4 quantizer & safety render gate** | Import Model Decision (2026-11-25) | Missing | Quantize converted models to FP8 or NVFP4 in the same import pipeline (`torchao` `TorchAoConfig` for Diffusers, NVIDIA ModelOpt for SGLang), then test-load and run a short sample render before prompting to delete or move the original. | New delta (+2–3d est.) | S (2–3d est.) |
| **Recursive model library & pre-render missing-piece check** | LIB-01–08, Model Library Rule | Missing | Background recursive scanner over user/shared model folders with `visibility` (`global`/`user`), `owner_id`, header checks, `.crdownload` skip, dependency packs, and pre-render blocker verifying text encoder, video VAE, audio VAE, and upscaler are present. | Already scoped in LIB-01–08; extended for multi-user visibility & preflight | M (5–6d est.) |
| **MiniMax H3 LoRA compatibility & routing** | LORA-01–09, Seed Hunter v3, 10Eros_Max | Missing | Filter LoRAs to project model + H3 partition (`fl2va` vs `ref2va`), surface `lora_compatibility_notes` warnings (e.g., MLP-only low-rank rules on `10Eros_Max`), enforce preflight checks, and support stage-1/2, upscale-only, and vocal slots. | Simplified (all imported weights & LoRAs are already normalized) | M (3–4d est.) |
| **H3 structured prompt IDE & RefMods** | PROMPT-01–09, Seed Hunter v3 JSON | Missing | Add 6-field `Singularity` prompt IDE (`subject_definitions`, `summary`, `retention_analysis`, `detailed_description` with `[Shot N]`/`<d>` tags, `overall_soundscape`, `non_diegetic_music`), `<Subject>/<Picture>/<Audio>` slots, and RefMod weighting. | From Seed Hunter v3 workflow JSON | M (4–5d est.) |
| **H3 multi-seed preview + 3D latent upscale** | MEDIA-05, Seed Hunter v3 Stage 1 & 2 | Partial | Extend `VideoClip` (like `Keyframe.candidate_asset_ids`) to store 3 preview seeds (`a`, `a+1000`, `a+2000`) at `0.2–0.4 MP`, promote winner into cached 3D latent upscale 2nd pass with rerollable seed and first/last frame export. | From Seed Hunter v3 workflow JSON | M (4–5d est.) |
| **H3 dialogue cloner & forced audio latent** | Seed Hunter v3 + Transcript | Missing | Add dialogue pre-gen mode (3 audio takes from `<Audio 1>`/`15–45s` vocal ref, `*emphasis*`, scene tone context), silence padding/trimming, and `VAEEncodeAudio` + `SetLatentNoiseMask` latent-lock mode. | From Seed Hunter v3 workflow JSON & transcript | M (4–5d est.) |
| **Seamless continuation & quality-reset continuity** | CONT-01–08, Seed Hunter v3 + Transcript | Missing | Implement `17n+5` (`5/22/39/56`) video+audio overlap conditioning, Turbo-OFF continuation preset, ~3-extension drift counter, camera-away redraw reset, pinned upscaled `<Picture 2>` last-frame reset, and stale downstream flags. | Simplified (single model family per project) | L (6–8d est.) |
| **LTX-2.5 joint A/V + IC-LoRA** | MEDIA-08, LTX23_PROVISIONING.md | Partial | Upgrade beyond `diffusers==0.33.1` `LTXPipeline` (`video.py`) to the Diffusers ≥ 0.40 LTX-2.5 path (`LTX2Pipeline` / `LTX25AutoBlocks`) with Gemma 4 projection and audio VAE. Prompt Relay and IC-LoRA Union/Ingredients remain capability-flagged until the pinned pipeline exposes them. | Unchanged (optional project core model) | L (6–9d est.) |
| **Wan 2.2, Wan Animate 2 & Bernini S2V** | MEDIA-08, WORKFLOW_PROFILES.md | Partial | Extend `WanPipeline` in `video.py` for Wan 2.2 TI2V high/low experts, and add Wan Animate 2 via `WanAnimate2Pipeline` (Diffusers ≥ 0.40). Bernini editing/reference and Bernini-R-S2V speech conditioning remain TBD until a Diffusers-native path is pinned. | Unchanged (optional project core model) | L (7–10d est.) |
| **True v2v source editing & ref2v** | GEN-03, GEN-04, GEN-05 | Missing | Add `ref2va` and `fl2va` to `VideoClip.mode` enum (`video_clip.py`), bind ordered multimedia references, and replace `video.py` line 187 `v2v` fallback (`source_video_path` is unused). | Simplified (modes constrained to project's `WorkflowProfile`) | M (4–6d est.) |
| **Validated output targets & limits** | OUTPUT-01–08, OUTPUT_POLICY.md | Missing | Bind `(res/MP, 17n+5 frames, fps)` limits to `Project.workflow_profile_id` at creation and enforce in shared UI/worker validator; separate native segment specs from final NLE export targets. | Simplified (validated against one fixed project profile) | S (2–3d est.) |
| **LLM / llama-server scene-plan assistant** | PROMPT-01–09, scene-plan.schema.json | Missing | Extend `prompt_service.py` with OpenAI-compatible / `llama-server` client, `scene-plan.schema.json` validation, H3 6-section / LTX / Wan renderers, and editable diff UI. | Simplified (renders prompts only for project's core model) | M (4–5d est.) |
| **UI-managed .env secrets & provider config** | ENV-01–06, PROMPT_PROVIDERS.md | Partial | Move shared admin-managed secrets (`VASTAI_API_KEY`, `HF_TOKEN`, `CIVITAI_API_KEY`, `SMTP_*`) out of SQLite `Setting` (`seed.py`) into atomic server `.env` (`0600`), while allowing optional per-user credential overrides. | Scoped for admin `.env` vs per-user overrides | S (2–3d est.) |
| **Saved / resumable jobs (Save/Load Job)** | JOB-01–08, LORA_LIBRARY_JOBS.md | Partial | Separate execution snapshots from `snapshot_service.py`; persist Stage-1 latent/seed checkpoints, single-project-model signatures, paused restore without auto-run, and path relinking. | Simplified (single model family signature per project) | M (3–4d est.) |
| **Standalone Video Upscaler & frame upscaler** | UPSCALE-01–08, Transcript | Missing | Implement chunked/tiled spatial video upscaling (`nmkdSiaxCX_200k` / AI upscaler, replacing v2-deferred note in `image.py`), RTX VSR detection, plus still-frame upscale hook (e.g., Qwen 2.1) for pinned last-frame quality resets. | Expanded slightly for pinned-frame upscale reset | M (4–6d est.) |
| **ASR subtitles, VoxCPM2 & SAM3.1** | MEDIA-01–03, PRD.md §9 | Partial | Keep MusicGen/AudioGen/TTS/wav2lip in `audio.py`; add Whisper/Qwen3-ASR, Qwen3-ForcedAligner, VoxCPM2 narration, SAM3.1 masks, and `caption` to `Track.type` enum (`track.py`). | Unchanged | L (6–8d est.) |
| **NLE seam grading, AnimeCadence & RIFE** | EDIT-05, Seed Hunter v3 + Transcript | Partial | Keep `interpolation.py` (RIFE 2x/4x) and `render_task`; add `AnimeCadence` 2D cadence limiter, frame-by-frame seam color/exposure/warmth matching, and compound-clip Gaussian/CineFocus blur+zoom seam transitions. | Downgraded from Has it to Partial by transcript seam-finishing needs | M (3–4d est.) |
| **Hardware profiling (sm_120) & attention tuning** | INSTALL-04, hardware_profile.py, Workflow JSON | Partial | `hardware_profile.py` already detects RTX 5090 (`sm_120`) and sets `eager` compile; add `llama-server` VRAM budget, sparse attention backend selection, and FP8/NVFP4 quantization capability checks. | Updated for TorchAO / ModelOpt capability checks | S (2–3d est.) |
| **Remote GPU rendering (Vast.ai / SSH)** | REMOTE-01–11, REMOTE_GPU_RENDERING.md | Partial | Replace empty stubs in `backend/routers/integrations.py` (`offers=[]`) with VM-mode SSH/TLS worker protocol, file sync, idempotency, and no-local-fallback lock. | Unchanged | L (8–12d est.) |
| **Native Win/Ubuntu Redis+venvs & blue-green UI** | INSTALL-01–10, UI_SPEC.md | Missing | Keep Redis, Celery priority queues, JWT/OAuth, and RBAC intact; remove Docker Redis hints by installing native Redis (`redis-server` on Ubuntu, Memurai/native Win32 Redis on Windows) in `scripts/install.sh` + `scripts/install.ps1`, add per-engine `.venvs`, and apply `#081A24`/`#36A9E8`/`#2DD4BF` theme. | Multi-user + native Redis without Docker (+1–2d in installers; saves queue rewrite) | L (9–12d est.) |

---

## Gap and Effort Breakdown

**Estimate reconciliation (41–58 days est.):** Keeping Celery, Redis priority queues, Redis pub/sub WebSockets, JWT/OAuth, and RBAC saves ~3–4 days in Phase 1 vs building a local queue. That saving is offset by +5–6 days of multi-user and routing work: Celery per-engine GPU routing (+1d Phase 3), multi-user library/Import RBAC and shared-folder reference checks (+1–2d Phase 2), admin `.env` vs per-user secret scoping (+1d Phase 1), and native Memurai/Ubuntu Redis bundling without Docker (+1–2d Phase 5).

### Phase Effort Distribution

| Phase | Estimate | Description |
|-------|----------|-------------|
| **Phase 3: H3 engine, Celery GPU routing & upscaler** | 10–14d | Per-engine Celery GPU workers + Seed Hunter (est.) |
| **Phase 5: NLE seams, Vast.ai & native Redis** | 9–12d | Seam grading, SSH VM, Memurai/Ubuntu Redis (est.) |
| **Phase 2: Import Model, RBAC & quantize** | 7–10d | Convert, FP8/NVFP4, safety gate, shared locks (est.) |
| **Phase 4: H3 IDE, RefMods, LoRA gate & ASR** | 6–9d | 6-field IDE, compatibility notes, Qwen3-ASR (est.) |
| **Phase 1: Project lock, Celery queues & library** | 5–7d | Reuses Celery/Redis/RBAC; adds scan & .env split (est.) |
| **Phase 0: H3 + LoRA + converter round-trip** | 4–6d | Prove pruned->Diffusers->quant + LoRA on 5090 (est.) |

### Status Distribution

- **Missing:** 14 areas
- **Partial:** 10 areas
- **Has it:** 0 areas

---

## Design Conflicts

Design conflicts between LVC and AIMoveMaker

| Conflict | Title | Detail | Status |
|----------|-------|--------|--------|
| **Project vs Clip** | AIMoveMaker per-clip model_id vs fixed Project.core_video_model | `VideoClip.model_id` and `Keyframe.model_id` allow mixed models on one timeline. Sidney's decision moves the choice onto `Project.core_video_model`, simplifying validation and assembly while requiring a schema migration. | Resolved by rule |
| **Inference format** | A:\\AIModelsProd ComfyUI pruned weights vs standard Diffusers/SGLang | Existing `A:\\AIModelsProd` H3 files are ComfyUI pruned ConvRot/NVFP4 checkpoints. Under the runtime-agnostic policy, AIMoveMaker does not add ComfyUI compatibility—Import Model converts and quantizes source files into standard Diffusers/SGLang layouts once. | Resolved by Import |
| **UI shell** | Browser React app vs native PySide6/Qt desktop | AIMoveMaker serves React/Vite from FastAPI (`backend/main.py`), whereas `PRD.md` §10 proposes PySide6/Qt. Keeping React inside a single-process desktop wrapper (`pywebview` or Tauri) preserves `TimelineView.tsx` and NLE seam tools. | Resolve in A00 |
| **Queue & Docker** | Celery + Redis kept, but Docker Redis replaced by native OS Redis + per-engine venvs | `setup.sh` suggests `docker run redis:7` while LVC bans Docker. Keep Celery priority queues (`celery_app.py`) and Redis pub/sub (`websockets.py`), install native Redis (`redis-server` on Ubuntu, Memurai/native Redis on Windows), and route Celery tasks to `.venvs/<engine>` GPU workers. | Refactor installers |
| **Multi-user library** | Flat global ModelRegistry vs per-user visibility & shared-folder Import/delete RBAC | With RBAC and Creative/Engineer handoffs kept active, `ModelRegistry` and `LoRARegistry` need `visibility` (`global`/`user`), `owner_id`, role-gated Import, and active-reference checks before deleting or moving originals in shared folders, plus admin `.env` vs user secret overrides. | Schema + RBAC |

---

## Key Risks and Unknowns

| Risk Category | Title | Detail | Status |
|--------------|-------|--------|--------|
| **Converter math** | Expanding pruned AdaLN & splitting fused QKV without quality loss | `10Eros_Max` headers confirm `adaln_basis [8, 2688]`, `adaln_t_table [1025, 8]`, and fused `qkv_proj [21504, 5376]`. Phase 0 must verify the exact reconstruction into standard unpruned Diffusers weights + FP8/NVFP4 quantization passes a visual/audio sample render. | High / Phase 0 gate |
| **Quantized int8_HQ** | Importing pre-quantized ComfyUI ConvRot checkpoints vs BF16 sources | ComfyUI `int8_HQ` files store Hadamard-rotated `I8` weights + `comfy_quant` tensors. Converting directly from BF16 is clean; handling `int8_HQ` requires either ConvRot un-rotation before FP8/NVFP4 re-quantization or guiding users to import the BF16 source. | Medium-High |
| **H3 quality drift** | 5-frame overlap lighting shifts & multi-extension contrast burn | Transcript evidence confirms H3 produces noticeable exposure/contrast/warmth jumps right after the 5-frame overlap and degrades over >3 extensions. Without built-in seam color-matching, redraw resets, or pinned 1080p last frames, long H3 continuations look burnt. | High / UX risk |
| **RTX 5090 sm_120** | 32 GB VRAM ceiling for unpruned/quantized DiT + Qwen3-VL + converter | Converting and quantizing a ~40–60 GB BF16 DiT into FP8/NVFP4 must run streaming/CPU-staged so it does not OOM 32 GB VRAM, and `hardware_profile.py` already disables `inductor` on `sm_120`. | Medium-High |
| **Remote Vast.ai** | Vast.ai integration is currently an empty stub | `integrations.py` returns `offers=[]` and `job_service.py` dispatches locally. SSH VM-mode transfer, idempotency, and no-local-fallback guard remain full builds. | Medium |

---

## Recommended Phased Build Order

```
Phase 0: P0 Spike       →   Phase 1: Lock & Lib      →   Phase 2: Import Model    →
H3 + LoRA + Converter       Project lock, Celery         Convert, quantize,
on 5090                     routes, scan                 RBAC gate

   ↓
Phase 3: H3 Workers     →   Phase 4: Prompts & ASR   →   Phase 5: NLE & Redis
GPU Celery, previews,       IDE, RefMods, LoRA           Seam grading, Vast,
17n+5                       notes                        Memurai
```

### Phase 0 — Prove H3 + LoRA + Pruned Converter Round-Trip on RTX 5090

**Estimate:** 4–6 days

Standalone spike outside ComfyUI on RTX 5090 (`sm_120`): take one pruned ComfyUI H3 checkpoint (`10Eros_Max` BF16 or `Comfy-Org` pruned), run the key-rename + QKV-split + pruned-AdaLN-expansion converter, quantize to FP8/NVFP4 (`torchao` `TorchAoConfig` for Diffusers vs NVIDIA ModelOpt for SGLang), load one converted LoRA, and verify a playable video+audio clip within 32 GB VRAM.

### Phase 1 — Project-level model lock, Celery queue routes & multi-user library scan

**Estimate:** 5–7 days

Keep Redis, Celery priority queues, JWT/OAuth, Redis pub/sub WS, and Creative/Engineer RBAC intact. Add immutable `Project.core_video_model` + `workflow_profile_id`, bind `OUTPUT-01–08` limits, add per-engine Celery queue routes (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`), move server secrets to admin `.env` (`0600`) with optional user overrides, and build recursive folder scanning (`LIB-01–08`) with `global`/`user` visibility and pre-render missing-piece checks.

### Phase 2 — Import Model, Converter, Quantizer & RBAC Safety Gate

**Estimate:** 7–10 days

Import Model lands here once the multi-user library and Celery import queue are ready: accept Civitai downloads or local files (gated by `admin`/`engineer` role), detect safetensors layout from headers, convert ComfyUI-packed models and ComfyUI/Kohya LoRAs to standard Diffusers layout, quantize inline to FP8 or NVFP4 (`torchao`/ModelOpt), run the mandatory test-load + short sample render gate streaming over Redis pub/sub WS, and enforce RBAC + zero active project references before deleting or moving originals.

### Phase 3 — Standard H3 Celery GPU Workers, Seed Hunter Stages, Continuity & Upscaler

**Estimate:** 10–14 days

Run standard Diffusers/SGLang `RuntimeAdapter`s (`t2va`/`fl2va`/`ref2va`, plus LTX-2.5/Wan, including Wan Animate 2 via `WanAnimate2Pipeline`) via engine-routed Celery GPU workers in `.venvs/<engine>` with VRAM lock coordination, 3-seed Stage-1 preview takes + Stage-2 3D latent upscale reroll, Voice Cloner dialogue pre-gen + `Force <Audio 1>` latent lock, `17n+5` video+audio overlap continuation with ~3-extension drift/reset helpers, and standalone Video Upscaler.

### Phase 4 — H3 Prompt IDE, RefMods, LoRA Gate & ASR/SAM Tools

**Estimate:** 6–9 days

Build 6-field `Singularity` Prompt IDE + `RefMods` controls + `llama-server`/OpenAI scene-plan expansion, enforce `base_model` + `lora_compatibility_notes` preflight warnings across Stage 1+2 / Upscale / Vocal slots, and add Whisper/Qwen3-ASR, ForcedAligner, VoxCPM2, SAM3.1, and `caption` timeline tracks.

### Phase 5 — NLE Seam Finishing, Vast.ai VM Worker & Docker-Free Native Redis Installers

**Estimate:** 9–12 days

Add `AnimeCadence`, adjacent-frame A/B seam color/exposure/warmth grading, and compound blur+zoom transitions in `TimelineView.tsx`; implement real Vast.ai SSH/TLS VM-mode worker (`REMOTE-01–11`), blue-green theme (`UI_SPEC.md`), and `scripts/install.sh` (native Ubuntu `redis-server`) + `scripts/install.ps1` (Memurai or native Win32 Redis service, zero Docker).

---

**End of Document**
