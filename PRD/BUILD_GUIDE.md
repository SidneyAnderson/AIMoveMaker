# Movie Maker Build Guide

**Agent-Ready Technical Implementation Guide**

**Version:** 1.0  
**Date:** 27 November 2026  
**Target:** Coding agents building Movie Maker features on AIMoveMaker v1 codebase  
**Foundation:** Addendum v1.3, Integration Map, actual AIMoveMaker code at `/workspace`

> **For coding agents:** Start with [`/AGENTS.md`](../AGENTS.md) for comprehensive instructions, hard rules, and the Phase 0 GPU test handoff. This guide provides implementation details; AGENTS.md provides the workflow.

---

## Table of Contents

1. [How to Use This Guide](#how-to-use-this-guide)
2. [Repository Map & Conventions](#repository-map--conventions)
3. [Hard Rules](#hard-rules)
4. [Phase Implementations (P0-P5)](#phase-implementations)

---

## How to Use This Guide

This guide is structured for a coding agent to implement Movie Maker features **incrementally** on the existing AIMoveMaker v1 codebase. Each phase breaks down into work packages with:

- **Goal:** What this work package achieves
- **Files to create/modify:** Real paths in `/workspace`
- **Interfaces/signatures:** Function/class signatures matching existing patterns
- **Data model & migration changes:** Exact SQLAlchemy model updates + Alembic migration steps
- **API endpoints:** FastAPI router additions/changes
- **Celery queue:** Which queue tasks run on (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`)
- **Tests to write:** Unit/integration test expectations
- **Acceptance criteria:** Tied to addendum requirement IDs
- **Definition of done:** Runnable checkpoint

**TBD Items:** Where the addendum marks something **TBD** or **estimate**, implement stub hooks or feature flags and move on.

---

## Repository Map & Conventions

### Directory Structure

```
/workspace/
├── backend/
│   ├── main.py                    # FastAPI app + lifespan + router mounting
│   ├── config.py                  # Settings (Pydantic BaseSettings)
│   ├── database.py                # SQLAlchemy async engine + Base
│   ├── dependencies.py            # JWT auth, get_current_user, require_admin
│   ├── celery_app.py              # Celery config + priority queues
│   ├── hardware_profile.py        # RTX 5090 detection, VRAM estimates
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── routers/                   # FastAPI routers
│   ├── services/                  # Business logic (async)
│   ├── tasks/                     # Celery tasks
│   ├── pipelines/                 # Generation pipelines
│   ├── migrations/                # Alembic migrations
│   └── integrations/              # External API clients
├── frontend/src/
│   ├── App.tsx                    # React Router + ProtectedRoute
│   ├── stores/                    # Zustand state management
│   ├── views/                     # Page-level components
│   ├── components/                # Reusable UI components
│   ├── api/                       # API client wrappers
│   └── hooks/                     # Custom React hooks
└── scripts/                       # Setup and installation scripts
```

### Key File Examples & Patterns

#### Model Pattern (`backend/models/*.py`)

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(
        Enum("draft", "creative_active", "pending_handoff", "eng_active", 
             "pending_return", "completed", name="project_state_enum"),
        default="draft"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
```

**Conventions:**
- UUIDs as strings (String(36))
- Explicit enum names for PostgreSQL compatibility
- created_at/updated_at timestamps with UTC
- Foreign keys with proper cascade rules

#### Schema Pattern (`backend/schemas/*.py`)

```python
from pydantic import BaseModel
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str
    description: str | None = None

class ProjectResponse(BaseModel):
    id: str
    title: str
    state: str
    created_at: datetime
    model_config = {"from_attributes": True}
```

#### Service Pattern (`backend/services/*.py`)

```python
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_project(db: AsyncSession, project_id: str) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
```

#### Router Pattern (`backend/routers/*.py`)

```python
from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.dependencies import require_admin
from backend.models.user import User

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    body: ProjectCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await create_project(db, admin.id, body.model_dump())
    return project
```

#### Celery Task Pattern (`backend/tasks/*.py`)

```python
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.celery_app import celery_app
from backend.config import get_settings

settings = get_settings()

def _publish_progress(job_id: str, progress_pct: int, current_step: int, total_steps: int):
    import redis
    r = redis.Redis.from_url(settings.REDIS_URL)
    payload = json.dumps({
        "job_id": job_id, 
        "progress_pct": progress_pct,
        "current_step": current_step,
        "total_steps": total_steps,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    r.publish(f"job:{job_id}", payload)

@celery_app.task(name="backend.tasks.example_task", max_retries=3)
def example_task(job_id: str, params: dict):
    sync_url = settings.DATABASE_URL.replace("+aiosqlite", "")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        # Update job, run generation, publish progress
        _publish_progress(job_id, 50, 1, 2)
        session.commit()
```

#### Migration Pattern (`backend/migrations/versions/*.py`)

```python
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Always use batch_alter_table for SQLite compatibility
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("new_field", sa.String(50), nullable=True))
    
    # Backfill if needed
    op.execute("UPDATE projects SET new_field = 'default' WHERE new_field IS NULL")
    
    # Make non-nullable if required
    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("new_field", nullable=False)

def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("new_field")
```

---

## Hard Rules

**These rules are non-negotiable. Violating them breaks the addendum contract.**

### 1. Multi-User Foundation: Keep Redis + Celery + 4 Personas + RBAC

- **Redis 7:** Remains Celery broker, pub/sub channel for WebSocket progress, presence backend
- **Celery 5:** Priority queues (`high`, `medium`, `default`, `low`) + new engine queues (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`)
- **4 Personas:** Admin, Creative, Engineer, Viewer (do NOT add/remove roles)
- **RBAC:** JWT auth, `get_current_active_user`, `require_admin`, role-gated state machine preserved
- **State Machine:** `draft` → `creative_active` → `pending_handoff` → `eng_active` → `pending_return` / `completed`

### 2. One Core Video Model Per Project (Immutable)

- Add `Project.core_video_model` (enum: `minimax_h3`, `ltx_2_5`, `wan_bernini`) set at creation
- Add `Project.workflow_profile_id` (FK) set at creation
- Both fields immutable—no PATCH allowed
- Remove `VideoClip.model_id` and `Keyframe.model_id` selectors

### 3. Runtime-Agnostic: Diffusers/SGLang Only, No ComfyUI

- Do NOT add ComfyUI as runtime
- Import Model converts ComfyUI artifacts → standard Diffusers layout once
- Use `diffusers>=0.40` or `sglang>=0.5.17`
- Replace `backend/pipelines/video.py` with `RuntimeAdapter` classes

### 4. Native Windows + Ubuntu, No Docker

- Phase 5: `install.sh` (Ubuntu `redis-server`) + `install.ps1` (Windows Memurai)
- No Docker, Docker Compose, or WSL Redis

### 5. Never Commit Secrets

- Secrets in admin `.env` (mode `0600`)
- API responses: return `{"is_set": true}` only, never values
- Never log secrets

### 6. TBD Items Are TBD

- Implement stubs/feature flags for TBD items
- Do NOT invent behavior
- Examples: pruned AdaLN math, ComfyUI int8_HQ import, H3 RefMods port, IC-LoRA

---

## Phase Implementations

This section provides detailed implementation steps for each phase. See `/workspace/PRD/MovieMaker_Integration_Map.md` for the complete file-by-file breakdown.

### Phase 0: H3 + LoRA + Converter Proof (4–6d) — **Owner Runs Locally**

**Goal:** Prove MiniMax H3 + LoRA + ComfyUI→Diffusers converter + FP8/NVFP4 quantization on RTX 5090 within 32 GB VRAM. Spike outside main app.

**⚠️ IMPORTANT: YOU DO NOT HAVE A GPU.**

Phase 0 is run by the repository owner (Sidney) on his local RTX 5090 PC using the test kit in `/phase0/`.

**Test Kit:** See [`/phase0/README.md`](../phase0/README.md)
- `phase0/env_check.py` — GPU/CUDA/driver/library check
- `phase0/vram_fit.py` — VRAM fit tests for all models
- `phase0/converter_check.py` — H3 converter prototype (stub)
- `phase0/run_all.ps1` / `phase0/run_all.sh` — Full test suite

**Your Workflow:**
1. **Build Phase 1+ assuming Phase 0 results will arrive later**
2. **If `phase0/results/<model>.json` exists:**
   - Read it and populate `ModelRegistry.fits_target_vram` from `vram_fit` field
   - Set `ModelRegistry.peak_vram_gb`, `load_time_sec` from results
3. **If results are missing:**
   - Default `fits_target_vram = false`
   - Models stay inactive until proven
   - UI shows "Phase 0 pending" or "VRAM fit: unknown"

**Never fake GPU measurements.** See AGENTS.md for the complete Phase 0 handoff protocol.

**Key Files (created by owner after tests):**
- `phase0/results/minimax_h3.json`
- `phase0/results/krea_2_turbo.json`
- `phase0/results/z_image_turbo.json`
- `phase0/results/flux_3_image_klein.json`
- ... etc (see `phase0/results/schema.json`)

**TBD Gate:** Pruned AdaLN expansion math must pass visual/audio test

---

### Phase 1: Project Lock, Celery Queues & Multi-User Library (5–7d)

**Goal:** Add immutable project core model, extend Celery queues, build library scanner, split admin secrets.

**Migration:** `<timestamp>_project_core_model_and_library_fields.py`

**Schema Changes:**
- `projects`: add `core_video_model`, `workflow_profile_id`
- `model_registry`: add `visibility`, `owner_id`, `base_model`, `layout_format`, `quantization`, `companion_ids`
- `lora_registry`: same + `lora_compatibility_notes`, `partition`
- `jobs`: add `workflow_profile_id`, `target_queue`, `checkpoint_state`

**New Models:**
- `backend/models/workflow_profile.py`

**Service Updates:**
- `project_service.py`: block `core_video_model` PATCH, add `clone_project()`
- `registry_service.py`: add `scan_model_folders()`, `check_missing_pieces()`
- `settings_service.py`: add `get_admin_env_vars()`, `set_admin_env_var()`

**Celery Queues:**
```python
# backend/celery_app.py
task_queues={
    "high": ..., "medium": ..., "default": ..., "low": ...,
    "gpu_h3": {"exchange": "gpu_h3", "routing_key": "gpu_h3"},
    "gpu_ltx": {"exchange": "gpu_ltx", "routing_key": "gpu_ltx"},
    "gpu_wan": {"exchange": "gpu_wan", "routing_key": "gpu_wan"},
    "gpu_audio": {"exchange": "gpu_audio", "routing_key": "gpu_audio"},
    "import_cpu": {"exchange": "import_cpu", "routing_key": "import_cpu"},
}
```

**Frontend Updates:**
- `ProjectsView.tsx`: require `core_video_model` in create modal
- `SettingsView.tsx`: admin secrets UI, model folder scan button

---

### Phase 2: Import Model, Converter, Quantizer & RBAC Safety Gate (7–10d)

**Goal:** Full Import Model pipeline with Civitai intake, conversion, quantization, test render, RBAC cleanup.

**New Services:**
- `backend/services/import_service.py`
- `backend/integrations/civitai.py`

**New Pipelines:**
- `backend/pipelines/converters/h3_converter.py` (from Phase 0 prototype)
- `backend/pipelines/converters/lora_converter.py`
- `backend/pipelines/quantizers/quantize_runner.py`

**New Tasks:**
- `backend/tasks/generation_tasks.py`: add `import_model_task`

**API Endpoints:**
- `POST /api/integrations/civitai/fetch` (download from Civitai)
- `POST /api/models/import` (gated: admin/engineer)
- `POST /api/models/import/{id}/finalize` (delete/move original)
- `GET /api/models/preflight/{project_id}` (missing-piece check)

**WebSocket Progress:**
- Channel: `import:{job_id}`
- Route: `/api/ws/imports/{job_id}`

**Frontend:**
- `frontend/src/views/ModelsView.tsx` (new)
- Import wizard: Civitai URL/file → header detect → convert → quantize → test render → cleanup

**Safety Gate:** Test-load + short render before allowing original file deletion

---

### Phase 3: H3 Celery GPU Workers, Seed Hunter Stages, Continuity & Upscaler (10–14d)

**Goal:** Replace `video.py` with `RuntimeAdapter`s, implement 3-seed Stage-1 previews, Stage-2 upscale, voice cloner, 17n+5 continuation.

**Replaced Files:**
- `backend/pipelines/video.py` → adapter dispatcher

**New Adapters:**
- `backend/pipelines/adapters/base.py`
- `backend/pipelines/adapters/h3_adapter.py` (`.venvs/h3`, `t2va`/`fl2va`/`ref2va`)
- `backend/pipelines/adapters/ltx_adapter.py` (`.venvs/ltx`, LTX-2.5)
- `backend/pipelines/adapters/wan_adapter.py` (`.venvs/wan`, Wan 2.2 + Animate 2)
- `backend/pipelines/adapters/upscale_adapter.py`

**Migration:** `<timestamp>_clip_previews_continuation_and_upscale.py`

**Schema Changes:**
- `video_clip`: add `preview_seeds_json`, `selected_preview`, `overlap_frames`, `drift_counter`
- `audio_clip`: add `dialogue_cloned`, `forced_latent`

**New Endpoints:**
- `POST /api/video-clips/{id}/promote-preview`
- `POST /api/video-clips/{id}/reroll-upscale`
- `POST /api/video-clips/{id}/continue`
- `POST /api/audio-clips/{id}/dialogue-clone`

**Celery Workers:**
- Start per-engine workers: `celery -A backend.celery_app worker -Q gpu_h3 -n h3@%h`
- Update `start.sh` to launch all engine workers

**Frontend:**
- `StoryboardView.tsx`: 3-seed preview cards, pick winner, Stage-2 reroll
- `TimelineView.tsx`: 17n+5 continuation, drift indicator, voice clone

---

### Phase 4: H3 Prompt IDE, RefMods, LoRA Gate & ASR/SAM Tools (6–9d)

**Goal:** Structured 6-field H3 prompts, RefMods, LoRA compatibility checks, ASR subtitles, VoxCPM2, SAM3.1.

**Migration:** `<timestamp>_structured_prompts_refmods_and_captions.py`

**Schema Changes:**
- `keyframes`/`video_clips`: add `structured_prompt_json`, `refmods_json`
- `tracks`: add `caption` to `type` enum

**Service Updates:**
- `prompt_service.py`: add `expand_scene_plan()`, OpenAI-compatible client
- `registry_service.py`: add `validate_lora_stack()` (compatibility notes check)

**Pipeline Updates:**
- `audio.py`: add Whisper/Qwen3-ASR, ForcedAligner, VoxCPM2 (run in `.venvs/audio`)
- `controlnet.py`: add SAM3.1 mask hook

**API Endpoints:**
- `POST /api/prompts/expand-scene-plan`

**Frontend:**
- `StoryboardView.tsx`: dual-buffer H3 Prompt IDE (6 sections), RefMods sliders, scene-plan diff
- `TimelineView.tsx`: LoRA drawers (Stage 1+2 / Upscale / Vocal), caption track, compatibility warnings

---

### Phase 5: NLE Seam Finishing, Vast.ai VM Worker & Native Redis Installers (9–12d)

**Goal:** Seam color grading, AnimeCadence, Vast.ai SSH worker, native Redis installers (no Docker).

**New Integrations:**
- `backend/integrations/vastai_vm.py`

**Pipeline Updates:**
- `interpolation.py`: add `AnimeCadence` 2D limiter
- `generation_tasks.py`: add per-clip LUT (brightness/contrast/warmth), blur+zoom transitions

**New Scripts:**
- `scripts/install.sh` (Ubuntu: `apt install redis-server`, start systemd, create `.venvs/*`)
- `scripts/install.ps1` (Windows: install Memurai, start service, create `.venvs/*`)

**Service Updates:**
- `job_service.py`: Vast.ai dispatch logic, SSH/TLS remote worker, file sync

**Frontend:**
- `TimelineView.tsx`: adjacent-clip A/B seam comparator, color/blur sliders
- Apply `#081A24`/`#36A9E8`/`#2DD4BF` theme in `index.css`

**Acceptance Check:** Clean Windows & Ubuntu installs start native Redis + Celery + FastAPI without Docker

---

## Testing Strategy

Each work package should include:

1. **Unit Tests** (`backend/tests/unit/`)
   - Service functions with mocked DB
   - Converter logic with sample headers
   - RBAC checks

2. **Integration Tests** (`backend/tests/integration/`)
   - API endpoint flows (create project → add clip → submit job)
   - Migration up/down
   - WebSocket progress streaming

3. **Frontend Tests** (optional, but recommended)
   - Component rendering
   - API client mocking
   - WebSocket reconnect logic

**Test Commands:**
```bash
pytest backend/tests/unit/
pytest backend/tests/integration/
```

---

## Common Pitfalls

1. **Forgetting `batch_alter_table`:** Always use for SQLite compatibility
2. **Missing JWT dependency:** Use `Annotated[User, Depends(get_current_active_user)]`
3. **Sync vs Async:** Celery tasks are synchronous; use sync engine
4. **WebSocket authentication:** Pass JWT as query param `?token=...`
5. **Enum migration:** Create PostgreSQL enum type before column on upgrade
6. **Secret leakage:** Never return secret values in API responses
7. **TBD implementation:** Stub with feature flag, do NOT invent behavior

---

## Development Workflow

1. **Create feature branch:** `git checkout -b feature/phase-1-project-lock`
2. **Generate migration:** `alembic revision -m "add_core_video_model"`
3. **Implement:** Models → Schemas → Services → Routers → Frontend
4. **Test:** Unit → Integration → Manual
5. **Apply migration:** `alembic upgrade head`
6. **Commit:** Small, logical commits per work package
7. **PR:** One PR per work package or phase

---

**End of BUILD_GUIDE.md**

For complete file-by-file integration details, see `/workspace/PRD/MovieMaker_Integration_Map.md`.

For UI/UX specifications, see `/workspace/PRD/UI_UX_SPEC.md`.

---

## v1.3 Addendum: Keyframe Image Model Defaults

**Added:** November 26, 2026

### Phase 0 Addition: Image Model VRAM Fit Checks

**Goal:** Test keyframe image models on RTX 5090 32 GB to record `fits_target_vram` flags for IMG-GATE-02.

**Models to test:**
- [Krea 2 Turbo](https://huggingface.co/krea/Krea-2-Turbo) - 12B, shipped T2I default
- [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) - 6B, shipped fallback
- [FLUX 3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) - 5.6B + 9B upsampler, shipped edit default
- [MiniMax-H3-Image](https://huggingface.co/MiniMaxAI/MiniMax-H3-Image) - 68.65 GB BF16, H3-profile default after gates

**Test script:** `scripts/spikes/image_model_vram_test.py`

**Key checks:**
- Krea 2 Turbo: 8-step T2I at 1024×1024 or 16:9 ~1080p
- Z-Image-Turbo: 9-step T2I (official: 16 GB fit)
- FLUX 3 Klein: test with/without 9B upsampler; offload if >32 GB
- MiniMax-H3-Image: 16:9 keyframe (vendor 5472×3072 TBD); quantization TBD

**Diffusers requirement:** `pip install diffusers>=0.43` (IMG-13)

**Acceptance:** Record `fits_target_vram` for each model; IMG-GATE-02 status known for H3-Image.

---

### Phase 1 Addition: Image Model Registry & Profile Fields

**Schema changes to `model_registry` (Section A18.4):**
```python
# Add to backend/models/model_registry.py:
license_spdx_or_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
license_authorization_status: Mapped[str] = mapped_column(
    Enum("not_required", "required_missing", "recorded", name="license_auth_status_enum"),
    default="not_required"
)
fits_target_vram: Mapped[bool] = mapped_column(Boolean, default=False)
image_role: Mapped[str | None] = mapped_column(
    Enum("t2i", "edit", "both", "training_base", name="image_role_enum"),
    nullable=True
)
machine_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
```

**Schema changes to `workflow_profile`:**
```python
# Add to backend/models/workflow_profile.py:
default_image_model_key: Mapped[str | None] = mapped_column(String(100), nullable=True)  # FK to ModelRegistry.machine_key
default_image_edit_model_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

**Migration:** `<timestamp>_add_image_model_fields.py` (after Phase 1 core migration)

---

### Phase 1 Addition: Image Model Registry Seed

**Seed shipped image models in `backend/seed.py`:**

```python
IMAGE_MODEL_PACK = [
    {
        "machine_key": "krea_2_turbo",
        "name": "Krea 2 Turbo",
        "type": "image",
        "image_role": "t2i",
        "hf_repo": "krea/Krea-2-Turbo",  # https://huggingface.co/krea/Krea-2-Turbo
        "license_spdx_or_name": "Krea 2 Community License",
        "license_authorization_status": "required_missing",  # Admin must acknowledge
        "fits_target_vram": False,  # Set true after Phase 0
        "is_active": False,  # Active after download + license ack
    },
    {
        "machine_key": "krea_2_raw",
        "name": "Krea 2 Raw",
        "type": "image",
        "image_role": "training_base",
        "hf_repo": "krea/Krea-2-Raw",  # https://huggingface.co/krea/Krea-2-Raw
        "license_spdx_or_name": "Krea 2 Community License",
        "license_authorization_status": "required_missing",
        "is_active": False,
    },
    {
        "machine_key": "z_image_turbo",
        "name": "Z-Image-Turbo",
        "type": "image",
        "image_role": "t2i",
        "hf_repo": "Tongyi-MAI/Z-Image-Turbo",  # https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
        "license_spdx_or_name": "Apache-2.0",
        "license_authorization_status": "not_required",
        "fits_target_vram": True,  # Official: 16 GB
        "is_active": False,
    },
    {
        "machine_key": "flux_3_image_klein",
        "name": "FLUX 3 Image Klein",
        "type": "image",
        "image_role": "both",
        "hf_repo": "black-forest-labs/flux-3-image-klein",  # https://huggingface.co/black-forest-labs/flux-3-image-klein
        "license_spdx_or_name": "FLUX Kommunity License v.1.0",
        "license_authorization_status": "required_missing",
        "fits_target_vram": False,  # Set true after Phase 0 (upsampler offload TBD)
        "is_active": False,
    },
    {
        "machine_key": "minimax_h3_image",
        "name": "MiniMax-H3-Image",
        "type": "image",
        "image_role": "both",
        "hf_repo": "MiniMaxAI/MiniMax-H3-Image",  # https://huggingface.co/MiniMaxAI/MiniMax-H3-Image
        "license_spdx_or_name": "MiniMax-H3-Image Community License",
        "license_authorization_status": "required_missing",  # US excluded territory
        "fits_target_vram": False,  # TBD: quantization required for 32 GB
        "is_active": False,
    },
]

async def seed_image_models(db: AsyncSession):
    for model_data in IMAGE_MODEL_PACK:
        result = await db.execute(select(ModelRegistry).where(ModelRegistry.machine_key == model_data["machine_key"]))
        if result.scalar_one_or_none() is None:
            model = ModelRegistry(**model_data)
            db.add(model)
    await db.commit()
```

**Update `WorkflowProfile` seed:**
```python
# h3_default profile:
"default_image_model_key": "minimax_h3_image",  # Only after IMG-GATE-01 & IMG-GATE-02
"default_image_edit_model_key": "minimax_h3_image",

# ltx_2_5_default and wan profiles:
"default_image_model_key": "krea_2_turbo",  # Falls back to z_image_turbo (IMG-03)
"default_image_edit_model_key": "flux_3_image_klein",
```

---

### Phase 1 Addition: Keyframe Model Defaulting Logic

**Service:** `backend/services/storyboard_service.py`

```python
async def resolve_image_model_default(db: AsyncSession, project: Project, is_edit: bool = False) -> ModelRegistry:
    """Resolve default image model for keyframe, applying IMG-06/IMG-07 gates."""
    profile = await db.get(WorkflowProfile, project.workflow_profile_id)
    key = profile.default_image_edit_model_key if is_edit else profile.default_image_model_key
    
    # Try profile default
    if key:
        result = await db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.machine_key == key)
            .where(ModelRegistry.is_active == True)
            .where(ModelRegistry.type == "image")
        )
        model = result.scalar_one_or_none()
        # Check gates (IMG-GATE-01, IMG-GATE-02)
        if model and model.license_authorization_status != "required_missing" and model.fits_target_vram:
            return model
    
    # Fallback: z_image_turbo (IMG-03)
    result = await db.execute(
        select(ModelRegistry)
        .where(ModelRegistry.machine_key == "z_image_turbo")
        .where(ModelRegistry.is_active == True)
    )
    fallback = result.scalar_one_or_none()
    if fallback:
        return fallback
    
    # No default available
    raise HTTPException(status_code=409, detail="image_default_unavailable")

async def create_keyframe(db: AsyncSession, storyboard_id: str, data: dict) -> Keyframe:
    """Create keyframe with defaulted model_id if omitted (IMG-06)."""
    storyboard = await get_storyboard(db, storyboard_id)
    project = await db.get(Project, storyboard.project_id)
    
    if "model_id" not in data or data["model_id"] is None:
        default_model = await resolve_image_model_default(db, project, is_edit=False)
        data["model_id"] = default_model.id
    
    keyframe = Keyframe(**data, storyboard_id=storyboard_id)
    db.add(keyframe)
    await db.commit()
    await db.refresh(keyframe)
    return keyframe
```

**Endpoint:** `POST /api/keyframes` (unchanged signature; `model_id` optional in request body)

---

### Phase 2 Addition: Import Model for Image Checkpoints

**Update:** `backend/services/import_service.py`

Extend Import Model to accept `type='image'` models:
- Detect image vs video layout from safetensors header
- Apply same convert/quantize/safety-gate flow
- Sample render: short still (1024×1024 or 16:9), not video
- Register with `type='image'`, `image_role`, `machine_key` if shipped family

**Endpoint:** `POST /api/models/import?type=image`

---

### Phase 3 Addition: Edit-from-Previous Keyframe

**Service:** `backend/services/storyboard_service.py`

```python
async def edit_from_previous_keyframe(
    db: AsyncSession,
    source_keyframe_ids: list[str],
    prompt: str,
    model_id: str | None = None
) -> Job:
    """Create edit job using previous keyframe(s) as references (IMG-07)."""
    source_keyframes = [await db.get(Keyframe, kid) for kid in source_keyframe_ids]
    project_id = source_keyframes[0].storyboard.project_id
    project = await db.get(Project, project_id)
    
    # Default to edit model
    if model_id is None:
        model = await resolve_image_model_default(db, project, is_edit=True)
        model_id = model.id
    
    # Create job with source images as references
    job = Job(
        type="keyframe_edit",
        project_id=project_id,
        model_id=model_id,
        params={
            "prompt": prompt,
            "reference_keyframe_ids": source_keyframe_ids,
        },
        target_queue="gpu_image",  # New queue for image jobs
    )
    db.add(job)
    await db.commit()
    return job
```

**Endpoint:** `POST /api/keyframes/edit-from-previous`

---

**v1.3 Summary:**
- Shipped image models: [Krea 2 Turbo](https://huggingface.co/krea/Krea-2-Turbo) (T2I default), [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) (fallback), [FLUX 3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) (edit default)
- H3-profile default: MiniMax-H3-Image (gated by license + VRAM fit)
- Phase 0: VRAM fit checks for all image models
- Phase 1: Registry seed, profile default fields, keyframe defaulting logic
- Phase 2: Import Model for image checkpoints
- Phase 3: Edit-from-previous workflow with multi-reference

