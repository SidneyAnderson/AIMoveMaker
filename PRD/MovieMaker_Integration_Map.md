# Integration Plan: Movie Maker into AIMoveMaker

**File-by-File Integration Blueprint**

**Version:** Updated 2026-11-26  
**Estimate:** 41–58 days across Phases 0–5  
**Summary:** File-by-file integration blueprint mapping the revised multi-user Phases 0–5 plan (41–58 days est.) onto AIMoveMaker's FastAPI, Redis/Celery, RBAC, SQLAlchemy, and React codebase.

---

## Table of Contents

1. [Integration Overview](#integration-overview)
2. [Component Inventory](#component-inventory)
3. [Seams and Conflicts](#seams-and-conflicts)
4. [Phase-by-Phase Integration Sequence](#phase-by-phase-integration-sequence)
5. [Integration Risks and Estimate Check](#integration-risks-and-estimate-check)

---

## Integration Overview

**Multi-user foundation preserved: Redis, Celery, RBAC, and WebSockets stay as core platform infrastructure**

Per Sidney's multi-user correction, AIMoveMaker keeps Redis, Celery (with priority queues), JWT/OAuth auth, Creative/Engineer handoff RBAC, and Redis pub/sub WebSocket progress untouched as the orchestration backbone. Only the video pipeline (`pipelines/video.py`) and external stubs (`integrations.py`) are replaced—while Celery expands to route jobs to isolated per-engine GPU workers (`.venvs/h3`, `.venvs/ltx`, `.venvs/audio`), RBAC governs Import/shared-folder cleanup, and native installers bundle Redis without Docker (Ubuntu `redis-server`, Windows Memurai/native Redis). Total estimate: 41–58 days.

This integration map aligns one-to-one with the revised gap analysis Page so every file edit, Alembic migration, Celery queue, API route, and UI update stays runnable at the end of every phase.

**Related Document:** [Bringing Long-Video-Creator into AIMoveMaker (Gap Analysis & Plan)](MovieMaker_Plan.md)

### Key Metrics

- **46** module groups inventoried (Covers full backend, frontend & scripts)
- **13 / 31** (Reuse as-is / Refactor) — Redis, Celery, RBAC & WS stay core
- **2 / 0** (Replace / Remove) — Only pipelines/video.py & integrations stubs
- **41–58d** updated build estimate (Net +2d vs 39–56d for multi-user + native Redis)

---

## Component Inventory

Every significant module in `/workspace/repos/AIMoveMaker` classified as Reuse as-is, Refactor, Replace, or Remove under the multi-user architecture.

### Backend Core & Infrastructure

| Component / File(s) | Layer | Disposition | Phase | Integration Reason |
|---------------------|-------|-------------|-------|-------------------|
| `backend/main.py` & `backend/database.py` | Backend Core | Refactor | Phase 1 | Keep FastAPI + async SQLAlchemy lifespan; start background model-folder scanner on boot and enable SQLite WAL mode. |
| `backend/config.py` | Backend Core | Refactor | Phase 1 | Keep `REDIS_URL` and JWT settings; add `MODEL_ROOTS`, `VENV_ROOT`, `ADMIN_ENV_PATH`, and per-engine Celery queue names. |
| `backend/logging_config.py` & `backend/errors.py` | Backend Core | Reuse as-is | Phase 1 | Rotating loguru logs and structured HTTP error envelope fit multi-user Movie Maker unchanged. |
| `backend/hardware_profile.py` & `backend/routers/hardware.py` | Backend Core | Refactor | Phase 0–1 | Keep RTX 5090 (`sm_120`) detection and `/api/hardware/estimate`; add FP8/NVFP4 TorchAO/ModelOpt checks and text-encoder offload VRAM math. |
| `backend/celery_app.py` | Backend Core | Refactor | Phase 1 & 3 | Keep Redis broker + priority queues (`high`/`medium`/`default`/`low`); add engine-routed GPU queues (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`). |
| `backend/dependencies.py` | Backend Core | Reuse as-is | Phase 1–2 | Keep JWT auth, `get_current_active_user`, and `require_admin` RBAC intact; reuse for Import Model and shared-folder deletion gates. |
| `backend/seed.py` | Backend Core | Refactor | Phase 1 | Keep admin bootstrap + non-secret defaults; seed `WorkflowProfile` defaults and move shared secret defaults to admin `.env`. |
| `backend/migrations/env.py` & `versions/*` | Backend Core | Refactor | Phase 1–4 | Keep Alembic batch-alter pattern (`9b0f7d2c4a91`); add 4 migrations for project core model, multi-user library/import fields, H3 clips, and prompt/caption columns. |

### Models & Schemas

| Component / File(s) | Layer | Disposition | Phase | Integration Reason |
|---------------------|-------|-------------|-------|-------------------|
| `backend/models/project.py` & `schemas/projects.py` | Models & Schemas | Refactor | Phase 1 | Keep `state` (`creative_active`/`eng_active`) and members; add immutable `core_video_model` + `workflow_profile_id` set at project creation. |
| `backend/models/model_registry.py`, `lora_registry.py` & `schemas/models.py` | Models & Schemas | Refactor | Phase 1–2 | Add `visibility` (`global`/`user`), `owner_id`, `base_model`, `lora_compatibility_notes`, `layout_format`, `quantization`, `partition`, and `companion_ids`. |
| `backend/models/video_clip.py`, `keyframe.py` & `schemas/timeline.py` | Models & Schemas | Refactor | Phase 1–3 | Drop per-clip `model_id` overrides; add `ref2va`/`fl2va` modes, 3-seed preview candidate IDs, `overlap_frames`, and drift/reset state. |
| `backend/models/track.py` & `audio_clip.py` | Models & Schemas | Refactor | Phase 3–4 | Add `caption` to `Track.type` enum (`track.py`) and dialogue voice-clone/forced-audio flags on `AudioClip`. |
| `backend/models/job.py`, `batch.py` & `schemas/jobs.py` | Models & Schemas | Refactor | Phase 1–3 | Keep priority/user_id/batching; add `workflow_profile_id`, `target_queue`, `checkpoint_state`, and `paused_resumable` fields for Save/Load Job. |
| `backend/models/snapshot.py` & `schemas/snapshots.py` | Models & Schemas | Reuse as-is | Phase 1 | Project snapshot tiers (`auto`, `manual`, `major`, `handoff`) work as built. |
| `backend/models/prompt_template.py`, `prompt_history.py` & `schemas/prompts.py` | Models & Schemas | Refactor | Phase 4 | Extend beyond flat positive/negative strings to store structured 6-section H3 `Singularity` prompts and `scene-plan.schema.json` diffs. |
| `backend/models/user.py`, `project_member.py`, `handoff_record.py`, `oauth_identity.py`, `user_invite.py`, `notification.py` | Models & Schemas | Reuse as-is | Phase 1 | Multi-user RBAC, Creative/Engineer handoffs, OAuth, invites, and notifications stay active as the app foundation. |
| `backend/models/asset.py`, `storyboard.py`, `timeline.py`, `setting.py` | Models & Schemas | Reuse as-is | Phase 1 | Core media/project entities stay intact (`setting.py` retains non-secret preferences; secrets move to `.env`). |

### Routers & Services

| Component / File(s) | Layer | Disposition | Phase | Integration Reason |
|---------------------|-------|-------------|-------|-------------------|
| `backend/routers/websockets.py` | Routers & Services | Refactor | Phase 1–2 | Reuse Redis pub/sub (`_redis_subscriber`), `job_manager`, and `presence_manager`; add `import:{job_id}` progress channel for Import safety gates. |
| `backend/routers/projects.py` & `services/project_service.py` | Routers & Services | Refactor | Phase 1 | Keep Creative/Engineer handoff state machine & member constraints; enforce `core_video_model` immutability and add `/projects/{id}/clone`. |
| `backend/routers/jobs.py` & `services/job_service.py` | Routers & Services | Refactor | Phase 1 & 3 | Keep Celery `send_task` dispatch; route jobs to engine-specific Celery GPU queues (`gpu_h3`, `gpu_ltx`, etc.) and run pre-render missing-piece check. |
| `backend/routers/model_registry.py`, `lora_registry.py` & `services/registry_service.py` | Routers & Services | Refactor | Phase 1–2 | Add multi-user visibility (`global` vs `user`), recursive folder scan, missing-piece preflight, Import Model APIs, and shared-reference delete locks. |
| `backend/routers/integrations.py` & `backend/integrations/__init__.py` | Routers & Services | Replace | Phase 2 & 5 | Replace empty Civitai/Vast.ai stubs (`offers=[]`) with real Civitai Model Importer API (Phase 2) and Vast.ai SSH/TLS VM client (Phase 5). |
| `backend/routers/settings.py` & `services/settings_service.py` | Routers & Services | Refactor | Phase 1 | Route admin-managed server secrets to atomic `0600` `.env` with masked readback and add optional per-user credential overrides. |
| `backend/routers/prompt_templates.py`, `prompt_history.py` & `services/prompt_service.py` | Routers & Services | Refactor | Phase 4 | Add OpenAI-compatible / `llama-server` scene-plan expansion and H3 6-section prompt compiler. |
| `backend/routers/storyboard.py`, `keyframes.py`, `timeline.py`, `tracks.py`, `video_clips.py`, `audio_clips.py`, `assets.py`, `batches.py`, `snapshots.py` | Routers & Services | Refactor | Phase 2–4 | Keep existing RBAC-checked CRUD; add Stage-1 3-preview promotion, `17n+5` continuation endpoints, RefMods metadata, and seam-grading params. |
| `backend/routers/auth.py`, `oauth.py`, `invites.py`, `users.py`, `notifications.py` & services | Routers & Services | Reuse as-is | Phase 1 | Multi-user auth, OAuth, invites, approvals, and user notifications remain active unchanged. |

### Pipelines & Tasks

| Component / File(s) | Layer | Disposition | Phase | Integration Reason |
|---------------------|-------|-------------|-------|-------------------|
| `backend/pipelines/video.py` | Pipelines & Tasks | Replace | Phase 0 & 3 | Hardcodes `diffusers==0.33.1` LTX/Wan and aliases `v2v` to `i2v`; replace with `RuntimeAdapter` bridge invoked inside per-engine Celery GPU workers. |
| `backend/tasks/generation_tasks.py` | Pipelines & Tasks | Refactor | Phase 2–3 | Keep Celery task decorators and `_publish_progress` (Redis pub/sub); dispatch engine steps to `.venvs/<engine>` runners and add `import_model_task`. |
| `backend/pipelines/image.py` | Pipelines & Tasks | Refactor | Phase 3 | Keep Diffusers T2I/I2I/Inpaint; implement v2-deferred upscaler (`nmkdSiaxCX_200k`/Qwen still upscale for pinned `<Picture 2>` resets). |
| `backend/pipelines/audio.py` | Pipelines & Tasks | Refactor | Phase 3–4 | Keep MusicGen/AudioGen/Coqui/wav2lip; run in `.venvs/audio` Celery worker and add Whisper/Qwen3-ASR, ForcedAligner & VoxCPM2. |
| `backend/pipelines/interpolation.py` | Pipelines & Tasks | Refactor | Phase 5 | Reuse RIFE 2x/4x + scene-cut detection as-is; add `AnimeCadence` 2D cadence limiter beside it. |
| `backend/pipelines/controlnet.py` | Pipelines & Tasks | Reuse as-is | Phase 3 | Depth/canny/pose/reference wrappers stay valid for image/LTX/Wan conditioning. |

### Frontend

| Component / File(s) | Layer | Disposition | Phase | Integration Reason |
|---------------------|-------|-------------|-------|-------------------|
| `frontend/src/App.tsx`, `stores/authStore.ts`, `LoginView.tsx`, `ChangePasswordView.tsx`, `AdminView.tsx` | Frontend | Reuse as-is | Phase 1–2 | Keep multi-user login, forced password change, and Admin user/role management; add `/models` route for Import Model. |
| `frontend/src/components/AppShell.tsx` & `stores/projectStore.ts` | Frontend | Refactor | Phase 1–2 | Keep `ProjectStateBanner`, presence, and role context; add Models/Import nav item and apply `#081A24`/`#36A9E8`/`#2DD4BF` theme. |
| `frontend/src/views/ProjectsView.tsx` & `api/projects.ts` | Frontend | Refactor | Phase 1 | Require `core_video_model` + `workflow_profile_id` in New Project modal and display immutable core model badge on project cards. |
| `frontend/src/views/StoryboardView.tsx` & `api/storyboard.ts` | Frontend | Refactor | Phase 3–4 | Keep Creative phase edit guards; remove per-shot model selector and add 6-field H3 Prompt IDE, RefMods, 3-seed previews, and Stage-2 reroll. |
| `frontend/src/views/TimelineView.tsx`, `api/jobs.ts` & `stores/jobStore.ts` | Frontend | Refactor | Phase 3–5 | Keep Engineer phase edit guards; add `17n+5` continuation + reset pins, pre-render missing-piece modal, `caption` track, and A/B seam grading. |
| `frontend/src/views/SettingsView.tsx` | Frontend | Refactor | Phase 1–2 | Split admin `.env` secrets vs user overrides, add shared model folder roots + recursive scan button, and link Import Model wizard. |
| `frontend/src/hooks/useWebSocket.ts` | Frontend | Reuse as-is | Phase 1–2 | JWT-authenticated WS hook with exponential backoff and Redis pub/sub streaming works unchanged. |
| `frontend/src/components/canvas/CanvasEditor.tsx` & `MaskCanvas.tsx` | Frontend | Reuse as-is | Phase 3–4 | Inpaint/outpaint mask tools already work and extend cleanly to SAM3.1 mask previews. |

### Root & Scripts

| Component / File(s) | Layer | Disposition | Phase | Integration Reason |
|---------------------|-------|-------------|-------|-------------------|
| `setup.sh`, `start.sh` & `requirements.txt` | Scripts & Deps | Refactor | Phase 1 & 5 | Drop `docker run redis:7`; install/start native Redis (Ubuntu `redis-server`, Windows Memurai/native Redis), launch per-engine Celery workers, and add `scripts/install.ps1` + `scripts/install.sh`. |

---

## Seams and Conflicts

Multi-user orchestration seams, options, and recommendations across Celery/Redis, RBAC, secrets, engine adapters, and native installers.

### Disposition Summary

- **Refactor:** 31 groups
- **Reuse as-is:** 13 groups
- **Replace:** 2 groups

### Critical Seams

| Seam / Conflict | Decision State | Options | Recommended Choice |
|-----------------|----------------|---------|-------------------|
| **1. Celery + Redis GPU-worker routing across isolated engine venvs** | Settled: Keep Redis + Celery | **Option A:** Run one monolithic Celery worker in a single venv (hits `torch`/`diffusers` conflicts with AudioCraft, H3, LTX-2.5). **Option B:** Keep Redis + Celery priority queues (`high`/`medium`/`default`/`low`) and run engine-routed Celery queues (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`) with workers inside `.venvs/<engine>` (or subprocess bridges). | Recommend Option B: preserves Celery priority queues, retries, and `generation_tasks.py` while isolating `diffusers>=0.40`/SGLang from `audiocraft`/Coqui. |
| **2. WebSocket live progress via Redis pub/sub** | Settled: Keep Redis pub/sub | **Option A:** Keep `websockets.py` (`_redis_subscriber`, `job:{job_id}`, `presence_manager`) as-is for generation only. **Option B:** Keep it and add `import:{job_id}` channel so Import Model conversion, quantization, and safety-render progress stream to `useWebSocket.ts` too. | Recommend Option B: reuses 100% of existing WS/Redis infrastructure for both video renders and Import Model jobs. |
| **3. Multi-user RBAC & Creative/Engineer handoff state machine** | Settled: Keep RBAC & handoffs | **Option A:** Leave RBAC only on projects/timelines while leaving models global and unguarded. **Option B:** Keep Creative/Engineer handoff locks (`creative_active`, `eng_active`) on projects and extend RBAC rules to model visibility, Import permissions, and shared-folder cleanup. | Recommend Option B: keeps collaboration coherent when Creative picks LoRAs/refs and Engineer runs Stage-2 upscales or imports models. |
| **4. Per-user model library & LoRA visibility + Import/Delete permissions** | New multi-user requirement | **Option A:** Single flat `ModelRegistry` where any user can delete or move files on disk. **Option B:** Add `visibility` (`global` vs `user`), `owner_id`, and `import_origin` to `ModelRegistry`/`LoRARegistry`: Admins/Engineers can import to shared roots, Creatives see global + own uploads, and deleting/moving an original on Import checks RBAC + active project references first. | Recommend Option B: prevents one user's Import cleanup from deleting a shared checkpoint referenced by another user's project. |
| **5. Admin-managed server `.env` vs per-user credentials** | Multi-user adaptation of ENV-01–06 | **Option A:** Put all secrets in SQLite `Setting` (`seed.py`) or one editable `.env` exposed to all users. **Option B:** Move shared infrastructure/token secrets (`VASTAI_API_KEY`, `HF_TOKEN`, `CIVITAI_API_KEY`, `SECRET_KEY`, `SMTP_*`) to admin-only atomic `.env` (`0600`), while optional per-user LLM/Civitai overrides live encrypted per user. | Recommend Option B: satisfies `ENV-01–06` without leaking admin tokens or letting non-admin users overwrite server Vast.ai/SMTP keys. |
| **6. Diffusers-only `video.py` (`v2v`->`i2v`) vs H3 Diffusers/SGLang RuntimeAdapters** | Required by Phase 0 & H3 | **Option A:** Patch `video.py` inside the single `venv`. **Option B:** Replace `video.py` with `RuntimeAdapter` implementations invoked by engine-specific Celery GPU workers (`H3DiffusersAdapter` / `H3SGLangAdapter`, `LTXAdapter`, `WanAdapter`) using standard unpruned+quantized weights. | Recommend Option B: cleans up the `v2v`->`i2v` bug and cleanly separates H3 (`diffusers>=0.40`/`SGLang`) from LTX-2.5 and Wan. |
| **7. `Project` schema (`core_video_model`, `workflow_profile_id`) & `ModelRegistry` merge** | Settled by Core Model & Import rules | **Option A:** Nullable columns + separate importer table. **Option B:** Alembic migration adds immutable `core_video_model` + `workflow_profile_id` on `projects` (backfilled on legacy rows, plus `/clone`), and extends `ModelRegistry`/`LoRARegistry` with `base_model`, `lora_compatibility_notes`, `layout_format`, `quantization`, `partition`, and `companion_ids`. | Recommend Option B: single source of truth for project creation, recursive scanning, Import Model, and pre-render missing-piece checks. |
| **8. Native Windows/Ubuntu installers bundling Redis without Docker** | Required by LVC INSTALL-01–10 + Redis | **Option A:** Keep `setup.sh` telling Windows/Linux users to run `docker run redis:7`. **Option B:** `scripts/install.sh` (Ubuntu) installs native `redis-server` via `apt`/systemd; `scripts/install.ps1` (Windows) installs/bundles native Redis via Memurai (Developer Edition) or native Windows Redis build as a local service—zero Docker. | Recommend Option B: honors the no-Docker rule while keeping Redis + Celery intact across both OS targets. |

---

## Phase-by-Phase Integration Sequence

Ordered steps per phase naming exact files, Alembic migrations, Celery queues, endpoints, UI views, and runnable acceptance checks.

### Phase 0 — Prove H3 + LoRA + Converter on RTX 5090

**Estimate:** 4–6 days

#### Step 0.1 — Create isolated H3 spike venv

**Estimate:** 1 day

**Files created** (outside core `venv`): `scripts/spikes/h3_roundtrip_test.py` and `.venvs/h3/` (`diffusers>=0.40`, `torchao`, or `sglang>=0.5.17` + `modelopt` on CUDA 12.8). Existing app, Redis, and Celery remain untouched.

#### Step 0.2 — Prove pruned ComfyUI -> Diffusers converter + FP8/NVFP4 quantizer

**Estimate:** 2 days

**Files created:** `backend/pipelines/converters/h3_converter.py` (prototype). Convert one pruned ComfyUI H3 checkpoint (`10Eros_Max` BF16 534-tensor or `Comfy-Org` pruned): rename keys, split `attn.qkv_proj` `[21504, 5376]` into Q/K/V, expand `adaln_basis`/`adaln_mean`/`adaln_t_table` into per-block AdaLN, and quantize via `TorchAoConfig` (FP8) vs ModelOpt (NVFP4).

#### Step 0.3 — Benchmark H3 + 1 converted LoRA on RTX 5090 & update hardware_profile.py

**Estimate:** 1–3 days

**Files changed:** `backend/hardware_profile.py` (add `supports_torchao_fp8`, `supports_modelopt_nvfp4`, and Qwen3-VL offload budget).

**Acceptance check:** converter round-trip + quantized H3 + 1 converted LoRA renders a playable video+audio MP4 on RTX 5090 (`sm_120`) within 32 GB VRAM, and existing AIMoveMaker still boots cleanly.

---

### Phase 1 — Project Lock, Celery Queues & Multi-User Library

**Estimate:** 5–7 days

#### Step 1.1 — Project core model & multi-user library schema migration

**Estimate:** 1.5–2 days

**Migration:** `backend/migrations/versions/<rev>_project_core_model_and_library_fields.py` via `op.batch_alter_table`.

Adds `core_video_model` (backfilled `'ltxv'`) and `workflow_profile_id` to `projects`; adds `visibility` (`global`/`user`), `owner_id`, `base_model`, `lora_compatibility_notes`, `layout_format`, `quantization`, `partition`, `companion_ids`, and `artifact_uid` to `model_registry` / `lora_registry`; adds `workflow_profile_id`, `target_queue`, and `checkpoint_state` to `jobs`.

**Files changed:** `models/project.py`, `models/model_registry.py`, `models/lora_registry.py`, `models/job.py`, `schemas/projects.py`, `schemas/models.py`, `schemas/jobs.py`.

#### Step 1.2 — Enforce project lock, keep RBAC/handoffs & split admin .env vs user secrets

**Estimate:** 1.5–2.5 days

**Files created:** `backend/profiles/catalog.py` (`WorkflowProfile` + `OUTPUT-01–08` validator).

**Files changed:** `config.py` (add `MODEL_ROOTS`, `VENV_ROOT`, `ADMIN_ENV_PATH`), `seed.py` (seed profiles, stop storing secret values in DB), `services/project_service.py` (block `core_video_model` edit on `PATCH`, keep `VALID_TRANSITIONS` + handoffs, add `clone_project`), `routers/projects.py` (`POST /api/projects/{id}/clone`), `services/settings_service.py` + `routers/settings.py` (admin-only atomic `0600` `.env` writes + optional per-user credential overrides).

#### Step 1.3 — Engine-routed Celery queues, recursive library scan & frontend wiring

**Estimate:** 2–2.5 days

**Files changed:** `celery_app.py` (keep priority queues + add `gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu` routing), `services/job_service.py` (pre-render missing-piece check + queue selection), `services/registry_service.py` (recursive scanner + user/global visibility filter + companion check), `routers/model_registry.py` (`POST /api/models/scan`, `GET /api/models/preflight/{project_id}`), `frontend/src/views/ProjectsView.tsx` (require `core_video_model` on create), `views/SettingsView.tsx` (admin `.env` secrets vs user overrides + model folder roots).

**Acceptance check:** multi-user login + Creative/Engineer handoff still works, Celery+Redis executes jobs, H3 project lock prevents model mixing, and render blocks if VAE/text encoder is missing.

---

### Phase 2 — Import Model, Converter, Quantizer & RBAC Safety Gate

**Estimate:** 7–10 days

#### Step 2.1 — Promote converter & inline FP8/NVFP4 quantizer + Celery import queue

**Estimate:** 2.5–3.5 days

**Files created:** `backend/services/import_service.py`, `backend/pipelines/converters/h3_converter.py`, `backend/pipelines/converters/lora_converter.py`, `backend/pipelines/quantizers/quantize_runner.py` (`TorchAoConfig` / ModelOpt in `.venvs/h3`).

**Files changed:** `tasks/generation_tasks.py` (add `import_model_task` streaming progress via Redis pub/sub channel `import:{job_id}`), `routers/websockets.py` (expose `/ws/imports/{job_id}`).

#### Step 2.2 — Civitai intake, Import RBAC, shared-folder reference checks & safety gate

**Estimate:** 2.5–4 days

**Files created:** `backend/integrations/civitai.py`.

**Files changed:** `routers/integrations.py` (`POST /api/integrations/civitai/fetch`), `routers/model_registry.py` (`POST /api/models/import` gated by role `admin`/`engineer`, `POST /api/models/import/{id}/finalize` enforcing `admin` or `owner_id` + zero active project/shared-folder references before deleting/moving originals).

**Migration:** `<rev>_add_import_jobs_and_provenance.py`.

#### Step 2.3 — Frontend Import Model Wizard & visibility/notes UI

**Estimate:** 2–2.5 days

**Files created:** `frontend/src/views/ModelsView.tsx` & `frontend/src/api/models.ts`.

**Files changed:** `App.tsx` (`/models` route), `AppShell.tsx` (Models/Import sidebar item), `SettingsView.tsx`.

Wizard shows header inspection (`534` vs `894` tensors, pruned AdaLN), WS progress via `useWebSocket.ts`, inline test-render player, visibility toggle (`global` vs `user`), `base_model` + `lora_compatibility_notes`, and RBAC-guarded Delete vs Move prompt.

**Acceptance check:** Engineer/Admin imports a pruned ComfyUI H3 BF16 file + LoRA, passes safety render, moves original safely only when unreferenced, and Creatives see the normalized model.

---

### Phase 3 — Standard H3 Celery GPU Workers, Seed Hunter Stages, Continuity & Upscaler

**Estimate:** 10–14 days

#### Step 3.1 — Replace pipelines/video.py with Celery GPU-worker RuntimeAdapters

**Estimate:** 3.5–4.5 days

**Files created:** `backend/pipelines/adapters/base.py`, `h3_adapter.py` (`.venvs/h3`, `t2va`/`fl2va`/`ref2va`, `shift=12/3`), `ltx_adapter.py` (`.venvs/ltx`, LTX-2.5 via `LTX2Pipeline` / `LTX25AutoBlocks`), `wan_adapter.py` (`.venvs/wan`, Wan 2.2 plus Wan Animate 2 via `WanAnimate2Pipeline`; Bernini-R-S2V remains TBD), `upscale_adapter.py`.

**File replaced:** `backend/pipelines/video.py` (adapter dispatcher; drops `v2v`->`i2v` alias).

**Files changed:** `tasks/generation_tasks.py` & `start.sh` (launch per-engine Celery GPU workers listening on `gpu_h3`/`gpu_ltx`/`gpu_wan`).

**Migration:** `<rev>_clip_previews_continuation_and_upscale.py`.

#### Step 3.2 — Seed Hunter Stage-1 previews, Stage-2 reroll, Voice Cloner & 17n+5 continuation

**Estimate:** 4.5–6.5 days

**Files changed:** `services/storyboard_service.py`, `services/timeline_service.py`, `pipelines/image.py` (still-frame upscaler for `<Picture 2>` pin), `routers/video_clips.py` (`promote-preview`, `reroll-upscale`, `continue`), `routers/audio_clips.py` (`dialogue-clone`), preserving Engineer/Creative role checks on all mutations.

#### Step 3.3 — Storyboard & Timeline UI for H3 workflow + pre-render gate

**Estimate:** 2–3 days

**Files changed:** `frontend/src/views/StoryboardView.tsx` (remove per-shot model selector; add 3-seed previews + Stage-2 reroll + two-version compare while keeping Creative lock), `views/TimelineView.tsx` (`17n+5` continuation, ~3-extension drift indicator, redraw/pinned-last-frame resets, dialogue clone + Forced Audio, missing-piece modal while keeping Engineer lock).

**Acceptance check:** Creative/Engineer flow runs end-to-end across Celery GPU workers to produce 3 previews, upscale winner, voice-cloned dialogue, and `17n+5` continuation.

---

### Phase 4 — H3 Prompt IDE, RefMods, LoRA Gate & ASR/SAM Tools

**Estimate:** 6–9 days

#### Step 4.1 — H3 Prompt IDE, RefMods & llama-server scene plan

**Estimate:** 2.5–3.5 days

**Migration:** `<rev>_structured_prompts_refmods_and_captions.py` (adds `structured_prompt_json` & `refmods_json` on `keyframes`/`video_clips`, `caption` to `Track.type`).

**Files changed:** `services/prompt_service.py` (OpenAI-compatible / `llama-server` client + `scene-plan.schema.json` validator + 6-field `Singularity` renderer), `routers/prompt_templates.py` (`POST /api/prompts/expand-scene-plan`), `frontend/src/views/StoryboardView.tsx` (dual-buffer H3 Prompt IDE + RefMods sliders + diff preview).

#### Step 4.2 — LoRA governance + ASR, VoxCPM2 & SAM3.1 audio/caption tracks

**Estimate:** 3.5–5.5 days

**Files changed:** `pipelines/audio.py` (run in `.venvs/audio` Celery worker; add Whisper/Qwen3-ASR, Qwen3-ForcedAligner, VoxCPM2), `pipelines/controlnet.py` (add SAM3.1 mask hook), `services/registry_service.py` (enforce `lora_compatibility_notes` warnings & partition/visibility checks), `frontend/src/views/TimelineView.tsx` (Stage 1+2 / Upscale / Vocal LoRA drawers + `caption` track).

**Acceptance check:** expand scene plan via LLM, see `10Eros_Max` LoRA warning, and generate ASR subtitles onto `caption` track.

---

### Phase 5 — NLE Seam Finishing, Vast.ai VM Worker & Docker-Free Native Redis Installers

**Estimate:** 9–12 days

#### Step 5.1 — NLE seam grading, AnimeCadence & FFmpeg transitions

**Estimate:** 2–3 days

**Files changed:** `pipelines/interpolation.py` (add `AnimeCadence`), `tasks/generation_tasks.py` (`render_task`: per-clip brightness/contrast/warmth/exposure LUT & cross-seam Gaussian blur + micro-zoom FFmpeg filters), `frontend/src/views/TimelineView.tsx` (adjacent-clip end/start frame A/B seam comparator + color/blur sliders) and `#081A24`/`#36A9E8`/`#2DD4BF` Tailwind tokens in `frontend/src/index.css`.

#### Step 5.2 — Vast.ai SSH/TLS VM worker & native Win/Ubuntu Redis-bundled installers

**Estimate:** 7–9 days

**Files created:** `backend/integrations/vastai_vm.py` (SSH/TLS remote Celery/worker protocol, transfer manifest, idempotency, strict no-local-fallback guard), `scripts/install.sh` (Ubuntu native `redis-server` + core venv + `.venvs/*` without Docker), `scripts/install.ps1` (Windows native Memurai or native Win32 Redis service + Python venvs + FFmpeg without Docker/WSL).

**Files changed:** `setup.sh`, `start.sh` (remove Docker Redis notes; launch core + engine Celery workers), `routers/integrations.py`, `services/job_service.py`.

**Acceptance check:** clean Windows & Ubuntu native installs start native Redis + Celery + FastAPI without Docker, seam-grade a 2-clip cut, and dispatch a job to Vast.ai.

---

## Integration Risks and Estimate Check

| Risk Category | Title | Detail | Status |
|--------------|-------|--------|--------|
| **Estimate check** | 41–58 day total reflects keeping Celery/Redis/RBAC + adding multi-user & native Redis scope | Keeping Celery, Redis pub/sub, JWT/OAuth, and RBAC saves ~3–4 days in Phase 1 vs rewriting a local queue, while adding Celery per-engine GPU routing (+1d P3), multi-user model visibility + shared-folder Import/delete locks (+1–2d P2), admin-vs-user secret scoping (+1d P1), and Docker-free native Redis packaging via Memurai/apt (+1–2d P5) puts the net total at 41–58 days (estimate). | 41–58d updated |
| **Windows Redis** | Native Redis licensing & service stability on Windows without Docker | Redis does not publish official Windows binaries; Memurai Developer Edition has free-tier limits/licensing nuances, while community Win32 Redis ports can lag upstream versions. `scripts/install.ps1` must validate Memurai/native Redis health and surface clear setup diagnostics. | Medium-High |
| **Celery GPU routing** | VRAM contention if multiple per-engine Celery workers run on one GPU | Running separate Celery worker processes for `.venvs/h3`, `.venvs/ltx`, and `.venvs/audio` risks OOM if two workers hold GPU contexts simultaneously. Use `--concurrency=1` with a shared Redis GPU mutex/lock (`gpu:lock`) or a single GPU Celery worker that spawns short-lived `.venvs/<engine>` subprocesses. | Critical design detail |
| **Shared cleanup** | Race conditions when deleting/moving originals after Import Model | In a multi-user setup, another user could start a job referencing a shared folder file while an Engineer finalizes Import cleanup. Wrap the pre-delete reference check and file move in a DB lock/transaction and soft-disable first. | Handle in Phase 2 |
| **Converter math** | Expanding pruned AdaLN & splitting fused QKV without quality loss | `10Eros_Max` headers confirm `adaln_basis [8, 2688]`, `adaln_t_table [1025, 8]`, and fused `qkv_proj [21504, 5376]`. Phase 0 must prove the exact reconstruction into standard unpruned Diffusers weights + FP8/NVFP4 quantization passes a sample render. | Phase 0 gate |

---

**End of Document**
