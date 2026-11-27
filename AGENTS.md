# Agent Instructions: AIMoveMaker Movie Maker Implementation

**Last Updated:** November 27, 2026  
**Target:** Coding agents implementing Movie Maker layers on AI Movie Maker v1

---

## Overview

You are implementing the Movie Maker layers on top of the existing AI Movie Maker v1 application. This is a **multi-user, local-first AI film studio** running on Ubuntu 22.04+ (WSL 2 on Windows hosts) with FastAPI backend, React frontend, Celery task queues, and Redis pub/sub.

**Runtime environment: WSL only.** The solution runs in WSL 2 (Ubuntu 22.04) on the owner's Windows 11 PC by design, and addendum v1.4 (INSTALL-03, amended November 27, 2026) makes WSL 2 the only Windows path. `setup.sh` and `start.sh` are bash scripts on purpose, so run them from the WSL shell. Do not build a native Windows installer, a PowerShell launcher, or a Memurai setup.

**Your role:** Build the features specified in the PRD addendum v1.4 using the existing codebase as the framework. You will extend, not replace, the working v1 application.

---

## Required Reading (In Order)

Before writing any code, read these documents in this exact order:

1. **`PRD/README.md`** — Document index, version history, key features, and document relationships
2. **`PRD/addendum/AIMoveMaker_PRD_Addendum_MovieMaker_v1.4.md`** — **THE AUTHORITATIVE BUILD CONTRACT**
   - This is the specification you must implement
   - Every requirement ID (PROFILE-01, LIB-02, IMPORT-05, etc.) is a contract
   - Where this conflicts with the original PRD, the addendum wins
3. **`PRD/BUILD_GUIDE.md`** — Implementation guide with:
   - Repo map and existing patterns to copy
   - Hard rules (never break these)
   - Phase-by-phase work packages with files, migrations, endpoints, queues, tests
   - v1.4 routing layer and per-family adapters (Section A19)
4. **`PRD/UI_UX_SPEC.md`** — UI/UX specification:
   - Screen layouts, components, states, role permissions
   - ASCII wireframes and mermaid diagrams
   - Core operations only; no per-model mode toggles
5. **`PRD/MovieMaker_Plan.md`** — Gap analysis and phased plan (historical 41–58 day estimate; v1.4 supersedes it with 49–67 days, estimate)
6. **`PRD/MovieMaker_Integration_Map.md`** — File-by-file reuse/refactor/replace map

**Historical context only:**
- `PRD/prd_text.txt` and `PRD/ai_movie_maker_prd_v1.docx` — Original v1 baseline (implemented)
- `PRD/history/AIMoveMaker_PRD_Addendum_MovieMaker_v1.1.md`, `v1.2.md`, and `v1.3.md` — Previous versions

**Where conflicts exist:** v1.4 addendum > v1.3 addendum > v1.2 addendum > v1.1 addendum > original PRD for the specific rows changed.

---

## Hard Rules (Never Break These)

### Architecture Constraints

1. **Keep Redis + Celery + Multi-User**
   - Redis 7 pub/sub for WebSocket progress updates
   - Celery 5 queues: keep the four v1 priority queues that `backend/celery_app.py` declares today (`high`, `medium`, `default`, `low`), and add the five engine queues in Phase 1 (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`)
   - JWT/OAuth authentication
   - DO NOT replace with single-user SQLite queues

2. **Keep the 4 Personas and Role-Gated State Machine**
   - **Personas:** Admin, Creative, Engineer, Viewer
   - **State machine:** `draft` → `creative_active` → `pending_handoff` → `eng_active` → `pending_return` → `completed`
   - See v1 Section 4 and addendum Section A3 for RBAC rules
   - DO NOT add a `solo_creator` bypass

3. **One Core Video Model Per Project (Immutable)**
   - Each project locks ONE core video model at creation: [`minimax_h3`](https://huggingface.co/MiniMaxAI/MiniMax-H3), [`ltx_2_5`](https://huggingface.co/Lightricks/LTX-2.5), or [`wan_bernini`](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B) (with [Bernini-R](https://huggingface.co/ByteDance/Bernini-R-Diffusers) editing/reference support)
   - This choice is immutable in place
   - Migration requires cloning into a new project
   - That lock covers the whole video pipeline: generate, continue, edit, consistency, and restore/refine
   - Image keyframe models (Krea 2, Z-Image, FLUX Klein, H3-Image) are a separate image layer, not a second video family
   - DO NOT allow switching a project's core model (PROFILE-03)
   - DO NOT mix video families inside one project

3a. **One User-Facing Operation Set**
   - Every family implements the same five operations: `generate_shot`, `continue_shot`, `edit_shot`, `keep_consistent`, `restore_refine` (addendum Section A19)
   - Family tools are internal: H3 FL2VA and Ref2VA (Ref2VA is its own SGLang service with `--model-variant ref2va`, or a Diffusers ModularPipeline; open release excludes Context-IR and Regenerate-2K); Wan 2.2 + Wan Animate 2 + [Bernini-R](https://huggingface.co/ByteDance/Bernini-R-Diffusers) (ByteDance code in `.venvs/bernini` because it pins `diffusers==0.35.2`); LTX-2.5 base + Creative Lab IC-LoRAs ([collection](https://huggingface.co/collections/Lightricks/ltx-25-creative-lab)), which need a Phase 0 Diffusers load or the documented fallback
   - The UI shows only the five operations. Engineer/Admin may see routing in diagnostics only
   - If `phase0/results/h3_ref2va.json`, `ltx_ic_lora.json`, or `bernini_r.json` is missing or not `"status": "pass"`, run the Section A19 fallback. Do not drop the operation and do not call ComfyUI
   - [Bernini-R-S2V](https://huggingface.co/rzgar/Bernini-R-S2V) stays out of scope

4. **Runtime-Agnostic: Diffusers/SGLang Only**
   - Use `"diffusers>=0.40"` or `"sglang>=0.5.17"`
   - DO NOT add ComfyUI runtime or ComfyUI nodes
   - ComfyUI-packed checkpoints are converted once at import, then run via Diffusers
   - See addendum A0.2 item 3

5. **Ubuntu / WSL 2 Only (No Docker for Standard Deploy)**
   - **Platform:** Ubuntu 22.04+. A Windows host runs the app inside WSL 2 only (addendum INSTALL-03)
   - **Redis:** native `redis-server` inside Ubuntu
   - DO NOT build a native Windows installer, `scripts/install.ps1`, or a Memurai setup
   - DO NOT require Docker for standard deployment (v1 Section 3.4 and addendum SECRET-05)
   - Docker is explicitly forbidden for Redis installers

6. **Never Commit Secrets or Print API Keys**
   - Secrets live in `.env` (mode `0600`), never in git
   - API responses return `{"is_set": true}`, never the value
   - Logs MUST NOT contain `CIVITAI_API_KEY`, `HF_TOKEN`, etc. (v1 Section 8.4)
   - See addendum Section A4.5 for secret handling
   - A gated Hugging Face repo is not a reason to copy weights elsewhere or to share a token. See **Gated Hugging Face models** below.

### Implementation Discipline

7. **Stub TBD Items Behind Feature Flags**
   - Where the addendum marks something **TBD** or **estimate**, implement a stub hook or feature flag
   - DO NOT invent model capabilities, VRAM limits, or quality claims not in the spec
   - Examples of TBD items: Prompt Relay, Bernini-R-S2V, Context-IR, Regenerate-2K, pruned AdaLN math (addendum A0.3)
   - IC-LoRA, Ref2VA, and Bernini-R are gated routes with fallbacks, not features to invent or to hide

8. **Phase 0 GPU Measurements Come From Owner**
   - **YOU HAVE NO GPU** — do not fake VRAM measurements
   - Read `phase0/results/*.json` (if present) to populate `ModelRegistry.fits_target_vram` etc.
   - If results are missing, or `status` is `gated_no_access`, leave the model pending and proceed to Phase 1+
   - `gated_no_access` is not a VRAM measurement. Do not set `fits_target_vram` from it
   - DO NOT mark a model as fitting 32 GB without actual Phase 0 results whose `status` is `pass` or `fail_vram`

9. **Use Existing Patterns**
   - Copy the structure of existing routers, services, Celery tasks, models, schemas
   - See BUILD_GUIDE.md "Repository Map & Conventions" for file locations and examples
   - DO NOT introduce new frameworks or libraries unless the spec requires them

10. **Follow Acceptance Criteria**
    - Every feature section in the addendum ends with acceptance criteria in GIVEN/WHEN/THEN format
    - A feature is complete when all its criteria pass
    - Write tests that verify these criteria

## Gated Hugging Face models

Some weights will not download until the repository owner accepts the license on huggingface.co while logged into their own account. A **401**, a **403**, or `huggingface_hub.errors.GatedRepoError` means that, and only that.

- It is not a model failure.
- It is not a reason to set `fits_target_vram` to false, and not a reason to set it to true.
- Treat `phase0/results/*.json` with `"status": "gated_no_access"` the same way you treat a missing Phase 0 result: leave the model pending and wait for the owner to accept the license and re-run.
- Do not work around the gate. No alternate mirrors, no re-uploads of the weights, no copied token, no token pasted into chat, logs, or git.
- Never print or commit `HF_TOKEN` or any `hf_...` string. Phase 0 redacts tokens before it writes `errors`.

`gated_no_access` is a different status from `missing_weights` and from `fail_vram`. The JSON includes `repo_id` and a hint to run `hf auth login` or `huggingface-cli login`, accept the license on that repo's page, and retry. `vram_fit` is omitted on purpose.

These repos returned `gated: auto` from the Hugging Face API on 2026-11-27. Every other repo this kit names (MiniMax H3, MiniMax-H3-Image, Wan 2.2 I2V, Wan 2.2 T2V, Wan Animate 2, Bernini-R, Bernini-R-Diffusers, Z-Image-Turbo, FLUX.2-klein-4B, Qwen-Image-2.1, Bernini-R-S2V) returned `gated: false`.

- [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5)
- Creative Lab collection ([Lightricks/ltx-25-creative-lab](https://huggingface.co/collections/Lightricks/ltx-25-creative-lab)), all 15 repos:
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Day-To-Night](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Day-To-Night)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Clean-Plate](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Clean-Plate)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Water-Simulation](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Water-Simulation)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Deblur](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Deblur)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Decompression](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Decompression)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Colorization](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Colorization)
  - [Lightricks/LTX-2.5-22b-LoRA-Cinemagraph](https://huggingface.co/Lightricks/LTX-2.5-22b-LoRA-Cinemagraph)
  - [Lightricks/LTX-2.5-22b-LoRA-Slow-Motion-Control](https://huggingface.co/Lightricks/LTX-2.5-22b-LoRA-Slow-Motion-Control)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-SDR-To-HDR](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-SDR-To-HDR)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Refine-Details](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Refine-Details)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Restore](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Restore)
  - [Lightricks/LTX-2.5-22b-IC-LoRA-Alpha-Gen](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Alpha-Gen)
- [krea/Krea-2-Turbo](https://huggingface.co/krea/Krea-2-Turbo)
- [krea/Krea-2-Raw](https://huggingface.co/krea/Krea-2-Raw)
- [black-forest-labs/flux-3-image-klein](https://huggingface.co/black-forest-labs/flux-3-image-klein)

---

## Repository Structure

```
AIMoveMaker/                       # Repo root (the PRD guides write this as /workspace)
├── backend/
│   ├── main.py                    # FastAPI app + lifespan + router mounting
│   ├── config.py                  # Settings (Pydantic BaseSettings)
│   ├── database.py                # SQLAlchemy async engine + Base
│   ├── dependencies.py            # JWT auth, get_current_user, require_admin
│   ├── celery_app.py              # Celery config + priority queues
│   ├── hardware_profile.py        # RTX 5090 detection, VRAM estimates
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── project.py
│   │   ├── user.py
│   │   └── ...
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── routers/                   # FastAPI routers
│   │   ├── projects.py
│   │   ├── auth.py
│   │   └── ...
│   ├── services/                  # Business logic (async)
│   ├── tasks/                     # Celery tasks
│   │   ├── generation_tasks.py
│   │   └── ...
│   ├── pipelines/                 # Generation pipelines
│   ├── migrations/                # Alembic migrations
│   ├── tests/                     # pytest suite (unit/, integration/)
│   └── integrations/              # External API clients (empty package in v1)
├── frontend/src/
│   ├── App.tsx                    # Main app + AppShell + routing
│   ├── stores/                    # Zustand stores
│   │   ├── authStore.ts
│   │   ├── projectStore.ts
│   │   └── ...
│   ├── components/                # React components (Shadcn/ui)
│   └── views/                     # Page-level views
│       ├── ProjectsView.tsx
│       └── ...
├── tests/                         # v1 phase verification scripts (run with python)
├── PRD/                           # All documentation
│   ├── README.md
│   ├── addendum/
│   │   └── AIMoveMaker_PRD_Addendum_MovieMaker_v1.4.md
│   ├── BUILD_GUIDE.md
│   ├── UI_UX_SPEC.md
│   └── ...
├── phase0/                        # Local GPU test kit (run by owner)
│   ├── README.md
│   ├── env_check.py
│   ├── vram_fit.py
│   ├── converter_check.py
│   ├── run_all.ps1 / run_all.sh
│   └── results/                   # JSON results (you read these)
├── AGENTS.md                      # This file
└── README.md                      # Project README (links to AGENTS.md)
```

---

## Phase 0 Handoff: Owner Runs GPU Tests Locally

**YOU DO NOT HAVE A GPU.** Phase 0 GPU measurements (VRAM fit checks, model loading, benchmark) are run by the repository owner (Sidney) on his local machine:

- **Hardware:** Windows 11 PC, RTX 5090 32 GB (sm_120), Intel Core Ultra 9 285K, CUDA 12.8+
- **Runtime for measurements:** WSL 2 Ubuntu 22.04 (`phase0/run_all.sh`), because that is where the app runs
- **Test kit:** `phase0/` directory (see `phase0/README.md` for instructions)
- **Results location:** `phase0/results/*.json`

### Your Workflow:

1. **Build Phase 1+ assuming Phase 0 results will arrive later:**
   - If `phase0/results/<model>.json` exists and `status` is `pass` or `fail_vram`, read it and populate:
     - `ModelRegistry.fits_target_vram` (true/false from `vram_fit` field)
     - `ModelRegistry.peak_vram_gb` (from `peak_vram_gb` field)
     - `ModelRegistry.load_time_sec` (from `load_time_sec` field)
   - If `status` is `gated_no_access`, do not read `vram_fit`. Wait for the owner.
   - If results are missing, or `status` is `gated_no_access`, default to:
     - Do not write `fits_target_vram` from that file. Leave the seed unknown (`false` only as the initial unset default, not as a measured failure)
     - `is_active = false` (models inactive until the owner accepts the license and re-runs)
     - UI shows "Phase 0 pending" or "Hugging Face license not accepted"

2. **Never fake GPU measurements:**
   - DO NOT set `fits_target_vram = true` without actual Phase 0 results
   - DO NOT guess peak VRAM or load times
   - DO NOT skip the results check and assume models fit

3. **Seed data with Phase 0 awareness:**
   - Initial registry seed has `fits_target_vram = false` for all models
   - After Phase 0 completes, re-run seed or migration to update flags from results JSON

**Result Schema:** See `phase0/results/schema.json` for the JSON format Phase 0 produces.

---

## Implementation Phases

Follow the phase sequence in BUILD_GUIDE.md:

Estimate: **49–67 days (estimate)**, superseding 41–58. See addendum Section A16.

- **Phase 0 (Owner, 6–9d):** GPU proof on RTX 5090 — H3 + LoRA + converter, plus `h3_ref2va`, `ltx_ic_lora`, and `bernini_r` gates
- **Phase 1 (You, 6–8d):** Project lock, `FamilyAdapter` / `CoreOperation` interface (continuation and consistency first), Celery queues, library
- **Phase 2 (You, 7–10d):** Import Model pipeline
- **Phase 3 (You, 14–18d):** Per-family adapters for all five core operations, then Seed Hunter extras. Bernini stays in its own venv
- **Phase 4 (You, 6–9d):** Prompt IDE, LoRA gate, ASR/SAM
- **Phase 5 (You, 10–13d):** NLE seams, Vast.ai, native Redis, Bernini venv installer

**Incremental delivery:** Each phase ends with a runnable checkpoint. Commit after each work package.

---

## Database Migrations

Use Alembic for all schema changes:

```bash
# Create migration
alembic revision --autogenerate -m "Add workflow_profile and model_registry extensions"

# Apply
alembic upgrade head
```

**Migration rules:**
- Use `op.batch_alter_table()` for SQLite compatibility (v1 uses SQLite in dev, Postgres in prod)
- Provide both `upgrade()` and `downgrade()`
- Test rollback before committing
- Never drop data without a backup path

---

## Testing

Run existing tests to verify you haven't broken v1:

```bash
# Backend tests: run from the repo root (pyproject.toml sets testpaths to backend/tests)
python -m pytest backend/tests -v

# v1 phase verification scripts: they call sys.exit(), so run them with python, not pytest
python tests/test_phase5.py
python tests/test_phase6.py
python tests/test_phase2_compliance.py   # needs the API running at http://localhost:8000

# Frontend: there is no "npm test" script, so the type check and build are the gate
cd frontend
npm run build
```

**Write tests for new features:**
- Unit tests: `backend/tests/unit/` (existing subfolders are `test_services/` and `test_pipelines/`)
- Integration tests: `backend/tests/integration/` (router tests go in `test_routers/`)
- End-to-end: Use existing test patterns (fixtures are in `backend/tests/conftest.py`)

**Acceptance criteria:** Every addendum feature section lists GIVEN/WHEN/THEN criteria. Write tests that verify these.

---

## Common Patterns

### 1. Adding a FastAPI Router

```python
# backend/routers/models.py
from fastapi import APIRouter, Depends
from backend.dependencies import get_current_user, require_admin
from backend.services.registry_service import RegistryService

router = APIRouter(prefix="/api/models", tags=["models"])

@router.get("/")
async def list_models(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    service = RegistryService(db)
    return await service.list_models(user)
```

Mount in `backend/main.py`:
```python
from backend.routers import models
app.include_router(models.router)
```

### 2. Adding a Celery Task

```python
# backend/tasks/generation_tasks.py
from backend.celery_app import celery_app

@celery_app.task(name="generation.render_h3", queue="gpu_h3")
def render_h3_task(job_id: str):
    # Celery tasks are synchronous. Reuse the v1 helpers already in this file:
    # _update_job_status() opens a sync SQLAlchemy Session, and
    # _publish_progress() publishes to the Redis channel job:{job_id}.
    _update_job_status(job_id, "running")
    # ... task logic
    _publish_progress(job_id, progress_pct=50, current_step=11, total_steps=22)
```

### 3. Adding a SQLAlchemy Model

```python
# backend/models/workflow_profile.py
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
import uuid

class WorkflowProfile(Base):
    __tablename__ = "workflow_profiles"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # ... more fields
```

### 4. Redis Pub/Sub for WebSocket Progress

```python
# Backend publishes
redis_client.publish(f"job:{job_id}", json.dumps({
    "progress": 75,
    "status": "rendering",
    "message": "Frame 18/22"
}))

# Frontend subscribes (useWebSocket hook already exists in v1)
const { data, isConnected } = useWebSocket(`/api/ws/jobs/${jobId}`);
```

---

## Secret Management

**Admin-managed `.env` (server-side):**
```bash
CIVITAI_API_KEY=sk-...
HF_TOKEN=hf_...
```

**Per-user overrides (optional):**
```python
# backend/services/settings_service.py
def get_civitai_key(user: User) -> str:
    # Check user override first, then admin .env
    return user.civitai_api_key_override or os.getenv("CIVITAI_API_KEY")
```

**Never return secrets in API responses:**
```python
# ❌ BAD
{"civitai_api_key": "sk-abc123"}

# ✅ GOOD
{"civitai_api_key_is_set": true}
```

**Never log secrets:**
```python
# ❌ BAD
logger.info(f"Using API key: {api_key}")

# ✅ GOOD
logger.info("Using configured API key (redacted)")
```

---

## Model Registry Seed

Seed the first-party model pack on startup or migration:

```python
# backend/seed.py
VIDEO_MODELS = [
    {"machine_key": "minimax_h3", "name": "MiniMax H3", "type": "video", "hf_repo": "MiniMaxAI/MiniMax-H3", ...},
    {"machine_key": "ltx_2_5", "name": "LTX-2.5", "type": "video", "hf_repo": "Lightricks/LTX-2.5", ...},
    {"machine_key": "wan_bernini", "name": "Wan 2.2 + Bernini-R", "type": "video", "hf_repo": "Wan-AI/Wan2.2-I2V-A14B", "bernini_hf_repo": "ByteDance/Bernini-R-Diffusers", ...},
]

IMAGE_MODELS = [
    {"machine_key": "krea_2_turbo", "name": "Krea 2 Turbo", "type": "image", "hf_repo": "krea/Krea-2-Turbo", ...},
    {"machine_key": "z_image_turbo", "name": "Z-Image-Turbo", "type": "image", "hf_repo": "Tongyi-MAI/Z-Image-Turbo", ...},
    {"machine_key": "flux_3_image_klein", "name": "FLUX 3 Image Klein", "type": "image", "hf_repo": "black-forest-labs/flux-3-image-klein", ...},
    {"machine_key": "minimax_h3_image", "name": "MiniMax-H3-Image", "type": "image", "hf_repo": "MiniMaxAI/MiniMax-H3-Image", ...},
]

# Full model links:
# VIDEO MODELS:
# - MiniMax H3: https://huggingface.co/MiniMaxAI/MiniMax-H3
# - LTX-2.5: https://huggingface.co/Lightricks/LTX-2.5 (gated)
# - Wan 2.2 I2V: https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B
# - Wan 2.2 T2V: https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B-Diffusers
# - Wan Animate 2: https://huggingface.co/Wan-AI/Wan2.2-Animate-14B
# - Bernini-R (wan_bernini editing/reference): https://huggingface.co/ByteDance/Bernini-R-Diffusers (requires ByteDance inference code)
# IMAGE MODELS:
# - Krea 2 Turbo: https://huggingface.co/krea/Krea-2-Turbo (gated)
# - Krea 2 Raw: https://huggingface.co/krea/Krea-2-Raw (gated, for LoRA training)
# - Z-Image-Turbo: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
# - FLUX 3 Image Klein: https://huggingface.co/black-forest-labs/flux-3-image-klein (gated)
# - MiniMax-H3-Image: https://huggingface.co/MiniMaxAI/MiniMax-H3-Image
```

**After Phase 0:** Read `phase0/results/*.json` and update `fits_target_vram` only when `status` is `pass` or `fail_vram`. `gated_no_access` stays pending.

---

## Questions or Blockers?

If you encounter:
- **TBD items** → Stub behind a feature flag and move on
- **Missing Phase 0 results, or `gated_no_access`** → Leave the model pending. Do not record a VRAM failure. Models stay inactive until the owner re-runs.
- **Unclear spec** → Follow the addendum; if truly ambiguous, implement the safest/simplest path
- **v1 conflict** → The addendum wins for changed rows (see Section A2); v1 wins elsewhere

**DO NOT:**
- Invent model capabilities not in the spec
- Skip Redis/Celery/RBAC
- Add ComfyUI runtime
- Fake GPU measurements
- Commit secrets

---

## Success Criteria

✅ You've succeeded when:
1. All addendum acceptance criteria pass
2. Existing v1 tests still pass (no regressions)
3. Phase 0 results (when available) are correctly consumed
4. No secrets in git or logs
5. The app still runs on Ubuntu 22.04+, including WSL 2 on a Windows host, without Docker (except optional Vast.ai burst)
6. The 4 personas and role-gated state machine still work
7. Projects are locked to one core video model at creation

**Definition of Done:** See BUILD_GUIDE.md work package definitions of done for each phase.

---

**Start here:** Read the PRD documents, review existing code patterns, and begin with Phase 1 (you can build it before Phase 0 results arrive). Good luck! 🎬
