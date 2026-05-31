# AI Movie Maker - Project Memory

## Project Overview
AI Movie Maker - end-to-end AI film production platform. PRD at `PRD/ai_movie_maker_prd_v1.docx`.

## Tech Stack
- **Backend**: FastAPI, Python 3.11+, SQLAlchemy 2.0 async, Alembic, Celery 5, Redis 7
- **Frontend**: React 18, Vite 5, Tailwind CSS 3, shadcn/ui, Zustand, TanStack Query
- **Database**: SQLite (dev), PostgreSQL 15+ (prod)
- **Auth**: JWT (python-jose), OAuth2 (Authlib), bcrypt cost 12
- **Logging**: Loguru, structured JSON
- **AI Pipelines**: HuggingFace Diffusers, AudioCraft, Coqui TTS, wav2lip, RIFE

## Build Phases (strict order)
1. Foundation - repo structure, models, migrations, seed
2. Backend API - stub endpoints with Pydantic schemas
3. Backend Logic - business logic, Celery, WebSocket
4. AI Pipelines - inference pipelines, hardware profiling
5. Frontend - React SPA with all views
6. Integration & Hardening

## 22 Entities
User, ProjectMember, Project, HandoffRecord, Snapshot, Storyboard, Keyframe, Asset, Timeline, Track, VideoClip, AudioClip, Batch, Job, ModelRegistry, LoRARegistry, Notification, PromptTemplate, PromptHistory, Setting, UserInvite, OAuthIdentity

## Key Conventions
- All PKs are UUID v4, all timestamps UTC
- Dark mode only in v1
- No Docker (bare venv deployment)
- Deploy path: /opt/aimoviemaker/
- Bootstrap admin: admin@localhost / admin (force password change)
- storage_path NEVER in API responses

## Gap Closure Progress (High → Low Priority Items)
Systematic close-out of pre-existing PRD implementation gaps (tracked 1-13):

1. ✅ Timeline persist + state gating foundation
2. ✅ Full dnd-kit hybrid drag/trim/reorder (Shift mode, hover grips, overlap visuals, snap, persistence)
3. ✅ Advanced notifications (email templates + user prefs + WS + hooks on jobs/handoffs/approvals/renders)
4. ✅ Audio waveform (peaks + caching + offset editing UI) + robustness fallbacks
5. ✅ PNG sequence export (backend ffmpeg+zip path + Timeline UI)
6. ✅ Batch generation queue UI (modal job multi-select + create + live counters via shared status hook)
7-13. Pending (hardware profiler polish, analytics charts, collaboration, ControlNet/LoRA editors, error UX, snapshots extra polish, final audit/EDL)

All 1-6 pass full tsc (0 errors) + py_compile. QA performed (static + flow traces); one pre-existing Settings analytics call-site defect corrected during QA.

New capabilities exposed: real-time batch progress, prompt history re-apply, candidate carousels, tiered snapshot restore, etc.
