# Movie Maker Build Guide

**Agent-Ready Technical Implementation Guide**

**Version:** 1.0  
**Date:** 26 November 2026  
**Target:** Coding agents building Movie Maker features on AIMoveMaker v1 codebase  
**Foundation:** Addendum v1.2, Integration Map, actual AIMoveMaker code at `/workspace`

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

### Phase 0: H3 + LoRA + Converter Proof (4–6d)

**Goal:** Prove MiniMax H3 + LoRA + ComfyUI→Diffusers converter + FP8/NVFP4 quantization on RTX 5090 within 32 GB VRAM. Spike outside main app.

**Key Files:**
- `.venvs/h3/` (isolated venv)
- `scripts/spikes/h3_roundtrip_test.py`
- `backend/pipelines/converters/h3_converter.py` (prototype)
- `backend/hardware_profile.py` (add capability checks)

**Core Tasks:**
1. Create isolated H3 venv with `diffusers>=0.40`, `torchao`
2. Prototype converter: detect layout, split QKV, expand AdaLN (TBD math)
3. Test FP8/NVFP4 quantization
4. Benchmark on RTX 5090: H3 + 1 LoRA < 32 GB VRAM
5. Update `hardware_profile.py` with `sm_120` detection

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
