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
