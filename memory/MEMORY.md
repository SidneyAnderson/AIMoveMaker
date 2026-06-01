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
**All 13 gaps systematically closed** (high → medium → low), followed by complete regression QA.

1. ✅ Timeline persist + state gating foundation
2. ✅ Full dnd-kit hybrid drag/trim/reorder (Shift mode, hover grips, overlap visuals, snap, persistence)
3. ✅ Advanced notifications (email templates + user prefs + WS + hooks on jobs/handoffs/approvals/renders)
4. ✅ Audio waveform (peaks + caching + offset editing UI) + robustness fallbacks
5. ✅ PNG sequence export (backend ffmpeg+zip path + Timeline UI)
6. ✅ Batch generation queue UI (modal job multi-select + create + live counters via shared status hook)
7. ✅ Hardware profiler UI + recommendations (rich card + live VRAM estimator)
8. ✅ Advanced Analytics dashboard (KPIs, CSS charts, success rate, failure reasons with guidance)
9. ✅ Real-time collaboration (presence users list + cursor_move protocol)
10. ✅ Advanced ControlNet/LoRA editors (multi-stack + preprocessor selector + sliders)
11. ✅ Deeper error handling + surfaced codes (central ERROR_CATALOG + rich UI surfacing)
12. ✅ Tiered snapshots extra polish (batch-complete trigger + better labels + restore UX; `snapshots.tier` migration added)
13. ✅ Final regression/audit + cleanups (full tsc/py_compile, TODO sweep, legacy removal, docs refresh)

**Latest QA (2026-05-31)**: Frontend build passes, all Python compiles clean, Phase 2/5/6 verification scripts pass, and `python -m pytest backend/tests -v` now runs real backend tests (3/3 passed) covering migration/schema parity and snapshot API regressions. All 13 gaps complete.

New capabilities exposed: real-time batch progress, prompt history re-apply, candidate carousels, tiered snapshot restore/filtering, etc.
