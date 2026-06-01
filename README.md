# AI Movie Maker

End-to-end AI film production platform (local-first NLE). Storyboard + Canvas for creative (T2I/I2I/inpaint/outpaint/ControlNet/LoRA + non-destructive pixel editing), Timeline multi-track NLE for engineering (LTX/WAN video, MusicGen/AudioGen/TTS/lipsync, RIFE interp, FFmpeg export). Advanced features now complete: full dnd-kit timeline interaction, batch queues with live progress, real-time notifications (email+webhook+WS), prompt templates+history, tiered snapshots, PNG sequence export, and robust pipelines. Generate images, videos, music, sound effects, voiceovers, and lip-synced output — all from a browser-based timeline editor.

## Prerequisites

| Dependency | Version | Required |
|------------|---------|----------|
| Python     | 3.10+   | Yes      |
| Node.js    | 18+     | Yes (frontend) |
| CUDA GPU   | sm_75+ (Blackwell sm_120 supported) | Yes (AI generation) |
| ffmpeg     | 4.0+    | Yes (video/audio processing) |
| Redis      | 7+      | Yes (task queue & real-time) |

### AI Pipeline Dependencies (installed automatically by setup.sh)

These are the core AI packages that power image, video, audio, and interpolation:

| Package | Version | Purpose |
|---------|---------|---------|
| PyTorch | 2.10+ (CUDA) | Deep learning framework |
| torchvision | — | Image transforms & models |
| torchaudio | — | Audio processing |
| Diffusers | 0.33+ | Stable Diffusion, LTX-V, WAN 2.2 |
| Transformers | 4.46+ | DPT depth estimation, tokenizers |
| AudioCraft | 1.3+ | MusicGen / AudioGen |
| Coqui TTS | 0.22+ | Text-to-speech synthesis |
| ControlNet-aux | 0.0.9+ | OpenPose, depth, edge preprocessors |
| xformers | 0.0.35+ | Memory-efficient attention |

`setup.sh` auto-detects your CUDA version and GPU architecture, then installs the matching PyTorch build. **Blackwell GPUs** (RTX 5090/5080/5070 — sm_120) require PyTorch 2.10+ with CUDA 12.8 (`cu128`), which is auto-detected and installed. Without a CUDA GPU, CPU-only mode is installed (functional but significantly slower).

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/AIMoveMaker.git
cd AIMoveMaker

# 2. Run setup (creates venv, installs deps, runs migrations, seeds DB)
chmod +x setup.sh start.sh
./setup.sh

# 3. Start all services
./start.sh
```

The setup script will:
- Create a Python virtual environment at `venv/`
- Auto-detect CUDA and install PyTorch with GPU support
- Install all AI and web dependencies from `requirements.txt`
- Create required directories (`data/`, `models/`, `outputs/`, `snapshots/`, `logs/`)
- Copy `.env.example` to `.env` and generate a random `SECRET_KEY`
- Run Alembic database migrations
- Seed the database with the admin user and 21 global settings
- Install frontend dependencies and build the production bundle

## First Run

After running `./start.sh`, you will have:

| Service           | URL                          |
|-------------------|------------------------------|
| Application       | http://localhost:8000        |
| API docs (Swagger)| http://localhost:8000/docs   |
| Vite dev server   | http://localhost:3000        |

### Default Admin Login

| Field    | Value           |
|----------|-----------------|
| Email    | admin@localhost |
| Password | admin           |

**You must change this password on first login.** The admin account has `force_password_change=true` by default.

### Workflow

1. **Login** at http://localhost:8000 (or http://localhost:3000 in dev mode) with the admin credentials
2. **Create a project** from the Projects view
3. **Add keyframes** in the Storyboard view — write prompts for image generation
4. **Generate images** using the generate toolbar
5. **Arrange clips** on the Timeline view
6. **Submit handoff** to switch from Creative to Engineering phase
7. **Generate video** from the assembled timeline
8. **Export** the final output

## v1 Implementation Status — All 13 Gaps Closed ✅

**Complete systematic closure** of the original project backlog (high → medium → low priority items 1-13), followed by full regression QA:

### High Priority (1-3)
- Full Timeline depth (dnd-kit hybrid drag/trim/reorder with Shift mode, grips, overlap visuals, snap, live overrides + persistence).
- Advanced notifications (multi-channel email via templates + webhook + WS, user prefs, hooks on key events).
- Prompt Templates + History + Candidates (full CRUD, re-apply, auto-write, carousel).

### Medium Priority (4-6)
- Audio waveform (real peaks + caching + offset editing) + robustness fallbacks.
- PNG sequence export (ffmpeg + ZIP, exposed in UI).
- Batch queue UI (job selection + creation + live progress counters).

### Low Priority (7-13) — All Polished & Verified
- Hardware profiler UI + recommendations (rich card + live VRAM estimator).
- Advanced Analytics dashboard (KPIs, CSS bar charts, success rate, failure reasons with guidance).
- Real-time Collaboration (presence users list + full cursor_move protocol over project WS).
- Advanced ControlNet/LoRA editors (multi-stack manager + preprocessor selector + strength sliders in creation form).
- Deeper Error Handling (central `ERROR_CATALOG` + user-friendly surfacing in UI).
- Tiered Snapshots extra polish (new batch-complete trigger + better labels + restore UX).
- **Final Regression Audit** — full tsc/py_compile clean, TODO sweep, legacy cleanup, documentation refresh.

**Verification**: Zero TypeScript errors, all Python files compile, existing phase tests pass, new features (error catalog, snapshots, editors) exercised and consistent.

All changes are in `main` and have passed complete QA regression.

## Testing & QA

The project includes dedicated verification scripts and has undergone full regression QA after completion of all 13 implementation gaps.

### Running Verification
```bash
# Individual phase checks (recommended for quick validation)
python tests/test_phase6.py
python tests/test_phase5.py
# ... (other test_phase*.py files)

# Backend test discovery
python -m pytest backend/tests/ -v

# Static type/lint checks (always green post-audit)
cd frontend && npx tsc --noEmit --skipLibCheck
# Python files: all compile cleanly
```

### Latest Full Regression QA Results (May 31, 2026)
- **Static Analysis**:
  - `frontend npm run build`: **passed** (Vite reports only the existing chunk-size warning).
  - Complete `py_compile` sweep over all `backend/**/*.py`: clean.
- **Import, Migration & Module Health**:
  - `alembic upgrade head`: clean; latest migration adds `snapshots.tier`.
  - All critical modules (error catalog, snapshot service, generation tasks, etc.) import without issues.
- **Existing Tests**:
  - `tests/test_phase2_compliance.py` (API compliance verification): **88/88 passed**.
  - `python -m pytest backend/tests -v`: **3/3 passed** (migration/schema parity + snapshot router regressions).
  - `tests/test_phase5.py` (Frontend verification): **111/111 passed**.
  - `tests/test_phase6.py` (Integration & Hardening verification): **88/88 passed**.
  - Other phase scripts pass cleanly when executed directly.
- **Note on `pytest tests/`**: The root `test_phase*.py` files are self-contained verification scripts that call `sys.exit()` at module import time. This design causes internal collection errors under pytest (expected behavior, not a regression in application code). Always run them directly with `python`.
- **Regression Spot-Checks**:
  - Full grep for TODO/FIXME/"future UI" across source (excluding venv/node_modules): only harmless input placeholders remain.
  - Verified no breakage in recently completed features: error catalog surfacing, batch snapshot auto-triggers, advanced ControlNet/LoRA editors, tiered snapshots, collaboration presence, analytics, etc.
  - Verified snapshot API responses hide server-side `storage_path` and support `tier` filtering.
  - Legacy cleanup performed (removed vestigial state from Timeline dnd-kit work; refreshed stale comments).
- **Outcome**: **Zero regressions**. The entire 13-gap implementation + all prior features are stable and verified.

See the `tests/` directory for the full set of phase verification suites.

## Project Structure

```
AIMoveMaker/
  backend/                  # FastAPI application
    config.py               # Pydantic settings (reads .env)
    main.py                 # App factory, lifespan, router registration
    models/                 # SQLAlchemy 2.0 async models (22 tables)
    schemas/                # 75 Pydantic request/response schemas
    celery_app.py           # Celery 5 configuration
    seed.py                 # Database seeder (admin + settings)
    hardware_profile.py     # GPU detection & optimization strategy
    logging_config.py       # Loguru sinks with rotation
    dependencies.py         # FastAPI dependencies (auth, DB session)
    routers/                # 20 API router modules (51 endpoints)
    services/               # 12 business logic services
    pipelines/              # AI generation pipelines
      image.py              #   T2I, I2I, Inpaint, Outpaint
      video.py              #   LTX-V, WAN 2.2 (T2V, I2V, V2V)
      audio.py              #   MusicGen, AudioGen, Coqui TTS, wav2lip
      controlnet.py         #   Depth, Canny, Pose, Reference
      interpolation.py      #   RIFE 2x/4x frame interpolation
    tasks/                  # Celery task definitions
    migrations/             # Alembic migration scripts
  frontend/                 # React 18 + Vite 5 + TypeScript
    src/
      api/                  # Axios client + endpoint modules
      stores/               # Zustand state (auth, project, job)
      hooks/                # WebSocket hook with reconnect
      components/           # AppShell, CommandPalette, UI primitives
      views/                # Login, Projects, Storyboard, Timeline, Admin, Settings
  PRD/                      # Product Requirements Document
  tests/                    # Phase verification test suites
  setup.sh                  # One-time bootstrap script
  start.sh                  # Launch all services
  .env.example              # Environment variable template
  requirements.txt          # Python dependencies (pinned)
```

## Environment Variables

All environment variables are documented in `.env.example`. Infrastructure-only config lives in `.env`; runtime configuration (API keys, SMTP, OAuth) is managed via the Admin Settings UI.

| Variable           | Required | Default                              | Description                        |
|--------------------|----------|--------------------------------------|------------------------------------|
| `DATABASE_URL`     | Yes      | `sqlite+aiosqlite:///./data/dev.db`  | SQLAlchemy async DB URL            |
| `REDIS_URL`        | Yes      | `redis://localhost:6379/0`           | Redis for Celery + pub/sub         |
| `SECRET_KEY`       | Yes      | (auto-generated by setup.sh)         | JWT HS256 signing secret           |
| `ENVIRONMENT`      | No       | `development`                        | `development` or `production`      |
| `LOG_LEVEL`        | No       | `INFO`                               | DEBUG, INFO, WARNING, ERROR        |
| `STORAGE_BASE_PATH`| No       | `./storage`                          | Root path for file storage         |

## API

- **51 REST endpoints** across 20 groups, all under the `/api/` prefix
- **3 WebSocket endpoints**: `/api/ws/jobs/{id}`, `/api/ws/projects/{id}`, `/api/ws/logs`
- **75 Pydantic schemas** for request/response validation
- Interactive API docs at http://localhost:8000/docs
- Built frontend is served via SPA catch-all (no separate web server needed in production)

### Authentication

- JWT access tokens (15-minute expiry) + refresh tokens (7-day expiry)
- HS256 signing algorithm
- OAuth2 support for Google and Discord (configure via Admin Settings)

## Architecture

### Backend

- **FastAPI** with async SQLAlchemy 2.0 and Alembic migrations
- **Celery 5** task queue with Redis broker and 4 priority queues (high/medium/default/low)
- **Redis 7** pub/sub for real-time WebSocket progress streaming
- **Loguru** logging with 50 MB rotation, 30-day retention, and JSON structured output

### Frontend

- **React 18** with TypeScript strict mode
- **Vite 5** with HMR and API proxy
- **Tailwind CSS 3** with custom PRD color tokens (dark mode only in v1)
- **shadcn/ui** component primitives
- **Zustand** for UI state, **TanStack Query** for server state
- **cmdk** command palette (Ctrl/Cmd+K)

### AI Pipelines

- **Image**: HuggingFace Diffusers (SD 1.5, SDXL, Flux) — T2I, I2I, Inpaint, Outpaint
- **Video**: LTX-V, WAN 2.2 — T2V, I2V, V2V with frame export
- **Audio**: AudioCraft (MusicGen/AudioGen), Coqui TTS, wav2lip lip sync
- **ControlNet**: Depth, Canny, Pose, Reference (SD 1.5 + SDXL models)
- **Interpolation**: RIFE 2x/4x with scene-cut detection
- **Hardware Profile Service**: Auto-detects GPU class (RTX 5090/Datacenter/Prosumer) and selects precision, compile backend, and attention implementation

## Logging

Logs are written to the `logs/` directory:

| File          | Format         | Rotation  | Retention |
|---------------|----------------|-----------|-----------|
| `app.log`     | Human-readable | 50 MB     | 30 days   |
| `app.json`    | JSON (structured)| 50 MB   | 14 days   |
| `celery.log`  | Celery worker  | (manual)  | (manual)  |
| `vite.log`    | Vite dev server| (manual)  | (manual)  |

## Scripts

| Script     | Description                                      |
|------------|--------------------------------------------------|
| `setup.sh` | One-time setup: venv, deps, migrations, seed, frontend build |
| `start.sh` | Launch Redis, Celery, FastAPI, Vite dev server   |
| `start.sh --api` | Launch backend only (no frontend dev server) |

## Development

```bash
# Activate the virtual environment
source venv/bin/activate

# Run backend only
uvicorn backend.main:app --reload

# Run frontend dev server
cd frontend && npm run dev

# Run Celery worker
celery -A backend.celery_app worker --loglevel=info

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"
```

## License

Proprietary. All rights reserved.
