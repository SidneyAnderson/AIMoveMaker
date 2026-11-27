# Agent Instructions: AIMoveMaker Movie Maker Implementation

**Last Updated:** November 27, 2026  
**Target:** Coding agents implementing Movie Maker layers on AI Movie Maker v1

---

## Overview

You are implementing the Movie Maker layers on top of the existing AI Movie Maker v1 application. This is a **multi-user, local-first AI film studio** running on Windows and Ubuntu with FastAPI backend, React frontend, Celery task queues, and Redis pub/sub.

**Your role:** Build the features specified in the PRD addendum v1.3 using the existing codebase as the framework. You will extend, not replace, the working v1 application.

---

## Required Reading (In Order)

Before writing any code, read these documents in this exact order:

1. **`PRD/README.md`** — Document index, version history, key features, and document relationships
2. **`PRD/addendum/AIMoveMaker_PRD_Addendum_MovieMaker_v1.3.md`** — **THE AUTHORITATIVE BUILD CONTRACT**
   - This is the specification you must implement
   - Every requirement ID (PROFILE-01, LIB-02, IMPORT-05, etc.) is a contract
   - Where this conflicts with the original PRD, the addendum wins
3. **`PRD/BUILD_GUIDE.md`** — Implementation guide with:
   - Repo map and existing patterns to copy
   - Hard rules (never break these)
   - Phase-by-phase work packages with files, migrations, endpoints, queues, tests
   - v1.3 addendum section for keyframe image models
4. **`PRD/UI_UX_SPEC.md`** — UI/UX specification:
   - Screen layouts, components, states, role permissions
   - ASCII wireframes and mermaid diagrams
   - v1.3 addendum for image model picker, license flows, edit-from-previous
5. **`PRD/MovieMaker_Plan.md`** — Gap analysis and phased plan (41-58 day estimate)
6. **`PRD/MovieMaker_Integration_Map.md`** — File-by-file reuse/refactor/replace map

**Historical context only:**
- `PRD/prd_text.txt` and `PRD/ai_movie_maker_prd_v1.docx` — Original v1 baseline (implemented)
- `PRD/history/AIMoveMaker_PRD_Addendum_MovieMaker_v1.1.md` and `v1.2.md` — Previous versions

**Where conflicts exist:** v1.3 addendum > v1.2 addendum > v1.1 addendum > original PRD for the specific rows changed.

---

## Hard Rules (Never Break These)

### Architecture Constraints

1. **Keep Redis + Celery + Multi-User**
   - Redis 7 pub/sub for WebSocket progress updates
   - Celery 5 priority queues: `high`, `medium`, `default`, `low`, `gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`
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
   - DO NOT allow switching a project's core model (PROFILE-03)

4. **Runtime-Agnostic: Diffusers/SGLang Only**
   - Use `"diffusers>=0.40"` or `"sglang>=0.5.17"`
   - DO NOT add ComfyUI runtime or ComfyUI nodes
   - ComfyUI-packed checkpoints are converted once at import, then run via Diffusers
   - See addendum A0.2 item 3

5. **Native Installers (No Docker for Standard Deploy)**
   - **Redis:** `redis-server` on Ubuntu, Memurai or native Redis build on Windows
   - DO NOT require Docker for standard deployment (v1 Section 3.4 and addendum SECRET-05)
   - Docker is explicitly forbidden for Redis installers

6. **Never Commit Secrets or Print API Keys**
   - Secrets live in `.env` (mode `0600`), never in git
   - API responses return `{"is_set": true}`, never the value
   - Logs MUST NOT contain `CIVITAI_API_KEY`, `HF_TOKEN`, etc. (v1 Section 8.4)
   - See addendum Section A4.5 for secret handling

### Implementation Discipline

7. **Stub TBD Items Behind Feature Flags**
   - Where the addendum marks something **TBD** or **estimate**, implement a stub hook or feature flag
   - DO NOT invent model capabilities, VRAM limits, or quality claims not in the spec
   - Examples of TBD items: IC-LoRA, Prompt Relay, Bernini-R-S2V, pruned AdaLN math (addendum A0.3)

8. **Phase 0 GPU Measurements Come From Owner**
   - **YOU HAVE NO GPU** — do not fake VRAM measurements
   - Read `phase0/results/*.json` (if present) to populate `ModelRegistry.fits_target_vram` etc.
   - If results are missing, default flags to `false`/`unknown` and proceed to Phase 1+
   - DO NOT mark a model as fitting 32 GB without actual Phase 0 results

9. **Use Existing Patterns**
   - Copy the structure of existing routers, services, Celery tasks, models, schemas
   - See BUILD_GUIDE.md "Repository Map & Conventions" for file locations and examples
   - DO NOT introduce new frameworks or libraries unless the spec requires them

10. **Follow Acceptance Criteria**
    - Every feature section in the addendum ends with acceptance criteria in GIVEN/WHEN/THEN format
    - A feature is complete when all its criteria pass
    - Write tests that verify these criteria

---

## Repository Structure

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
│   └── integrations/              # External API clients (Civitai, HF)
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
├── tests/                         # Existing tests
├── PRD/                           # All documentation
│   ├── README.md
│   ├── addendum/
│   │   └── AIMoveMaker_PRD_Addendum_MovieMaker_v1.3.md
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
- **Test kit:** `phase0/` directory (see `phase0/README.md` for instructions)
- **Results location:** `phase0/results/*.json`

### Your Workflow:

1. **Build Phase 1+ assuming Phase 0 results will arrive later:**
   - If `phase0/results/<model>.json` exists, read it and populate:
     - `ModelRegistry.fits_target_vram` (true/false from `vram_fit` field)
     - `ModelRegistry.peak_vram_gb` (from `peak_vram_gb` field)
     - `ModelRegistry.load_time_sec` (from `load_time_sec` field)
   - If results are missing, default to:
     - `fits_target_vram = false`
     - `is_active = false` (models inactive until proven)
     - UI shows "Phase 0 pending" or "VRAM fit: unknown"

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

- **Phase 0 (Owner):** GPU proof on RTX 5090 — H3 + LoRA + converter + VRAM fit checks (run locally by Sidney)
- **Phase 1 (You):** Project lock, Celery queues, multi-user library, workflow profiles
- **Phase 2 (You):** Import Model pipeline (Civitai intake, conversion, quantization, safety gate)
- **Phase 3 (You):** Generation engines (H3, LTX-2.5, Wan 2.2), Seed Hunter, continuation
- **Phase 4 (You):** Seam finishing, blur/zoom transitions, RIFE interpolation, upscale
- **Phase 5 (You):** Integration polish, performance tuning, documentation

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
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests (if present)
cd frontend
npm test
```

**Write tests for new features:**
- Unit tests: `tests/unit/test_<feature>.py`
- Integration tests: `tests/integration/test_<workflow>.py`
- End-to-end: Use existing test patterns (look at `tests/` for examples)

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
from backend.database import async_session

@celery_app.task(name="generation.render_h3", queue="gpu_h3")
def render_h3_task(job_id: str):
    # Use sync DB session in Celery tasks
    with async_session() as db:
        # ... task logic
        redis_client.publish(f"job:{job_id}", json.dumps({"progress": 50}))
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

**After Phase 0:** Read `phase0/results/*.json` and update `fits_target_vram` flags.

---

## Questions or Blockers?

If you encounter:
- **TBD items** → Stub behind a feature flag and move on
- **Missing Phase 0 results** → Default to `fits_target_vram = false`, models inactive
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
5. The app still runs on Windows + Ubuntu without Docker (except optional Vast.ai burst)
6. The 4 personas and role-gated state machine still work
7. Projects are locked to one core video model at creation

**Definition of Done:** See BUILD_GUIDE.md work package definitions of done for each phase.

---

**Start here:** Read the PRD documents, review existing code patterns, and begin with Phase 1 (you can build it before Phase 0 results arrive). Good luck! 🎬
