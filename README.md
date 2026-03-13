# AI Movie Maker

End-to-end AI film production platform. Generate images, videos, music, sound effects, voiceovers, and lip-synced output — all from a browser-based timeline editor.

## Prerequisites

| Dependency | Version | Required |
|------------|---------|----------|
| Python     | 3.11+   | Yes      |
| Node.js    | 18+     | Yes (frontend) |
| Redis      | 7+      | Yes (task queue & real-time) |
| CUDA GPU   | sm_75+  | Recommended (AI pipelines) |

### Optional (AI pipeline dependencies)

These are loaded conditionally and only needed for GPU-accelerated generation:

- PyTorch 2.0+ with CUDA support
- HuggingFace Diffusers, Transformers
- AudioCraft (MusicGen / AudioGen)
- Coqui TTS
- wav2lip
- RIFE (frame interpolation)

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
- Install all Python dependencies from `requirements.txt`
- Create required directories (`data/`, `models/`, `outputs/`, `snapshots/`, `logs/`)
- Copy `.env.example` to `.env` and generate a random `SECRET_KEY`
- Run Alembic database migrations
- Seed the database with the admin user and 21 global settings
- Install frontend dependencies and build the production bundle

## First Run

After running `./start.sh`, you will have:

| Service           | URL                          |
|-------------------|------------------------------|
| FastAPI (backend) | http://localhost:8000        |
| API docs (Swagger)| http://localhost:8000/docs   |
| Vite (frontend)   | http://localhost:5173        |

### Default Admin Login

| Field    | Value           |
|----------|-----------------|
| Email    | admin@localhost |
| Password | admin           |

**You must change this password on first login.** The admin account has `force_password_change=true` by default.

### Workflow

1. **Login** at http://localhost:5173 with the admin credentials
2. **Create a project** from the Projects view
3. **Add keyframes** in the Storyboard view — write prompts for image generation
4. **Generate images** using the generate toolbar
5. **Arrange clips** on the Timeline view
6. **Submit handoff** to switch from Creative to Engineering phase
7. **Generate video** from the assembled timeline
8. **Export** the final output

## Project Structure

```
AIMoveMaker/
  backend/                  # FastAPI application
    config.py               # Pydantic settings (reads .env)
    main.py                 # App factory, lifespan, router registration
    models.py               # SQLAlchemy 2.0 async models (22 tables)
    schemas.py              # 75 Pydantic request/response schemas
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
| `STORAGE_BASE_PATH`| No       | `/opt/aimoviemaker`                  | Root path for file storage         |

## API

- **51 REST endpoints** across 20 groups
- **3 WebSocket endpoints**: `/ws/jobs/{id}`, `/ws/projects/{id}`, `/ws/logs`
- **75 Pydantic schemas** for request/response validation
- Interactive API docs at http://localhost:8000/docs

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
