import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Configure logging with rotation — PRD Phase 6 requirement
    from backend.logging_config import configure_logging
    configure_logging()
    from loguru import logger
    logger.info(
        "AI Movie Maker starting",
        extra={"environment": settings.ENVIRONMENT},
    )
    # Hardware Profile Service — runs at server startup per PRD §3.3
    try:
        from backend.hardware_profile import get_hardware_profile
        get_hardware_profile()
    except Exception as e:
        logger.warning(f"Hardware profile detection skipped: {e}")
    yield
    # Shutdown
    logger.info("AI Movie Maker shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Movie Maker",
        description="End-to-End AI Film Production Platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API sub-router under /api prefix ────────────────────────────────
    # All REST and WebSocket endpoints are served under /api/* so the
    # frontend (served at /) never collides with API paths.
    api = APIRouter(prefix="/api")

    from backend.routers import (
        assets,
        audio_clips,
        auth,
        batches,
        integrations,
        invites,
        jobs,
        keyframes,
        lora_registry,
        model_registry,
        notifications,
        oauth,
        projects,
        prompt_history,
        prompt_templates,
        settings,
        hardware,
        snapshots,
        storyboard,
        timeline,
        tracks,
        users,
        video_clips,
        websockets,
    )

    api.include_router(auth.router)
    api.include_router(oauth.router)
    api.include_router(invites.router)
    api.include_router(users.router)
    api.include_router(projects.router)
    api.include_router(storyboard.router)
    api.include_router(keyframes.router)
    api.include_router(timeline.router)
    api.include_router(tracks.router)
    api.include_router(video_clips.router)
    api.include_router(audio_clips.router)
    api.include_router(assets.router)
    api.include_router(jobs.router)
    api.include_router(batches.router)
    api.include_router(model_registry.router)
    api.include_router(lora_registry.router)
    api.include_router(integrations.router)
    api.include_router(settings.router)
    api.include_router(snapshots.router)
    api.include_router(notifications.router)
    api.include_router(websockets.router)
    api.include_router(prompt_templates.router)
    api.include_router(prompt_history.router)
    api.include_router(hardware.router)

    app.include_router(api)

    # ── Static file serving (production) ────────────────────────────────
    # Serve the built frontend from frontend/dist/ when available.
    # In development, Vite dev server handles this instead.
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "frontend" / "dist"
    if dist_dir.is_dir():
        from fastapi.responses import FileResponse, JSONResponse

        # Catch-all for SPA — serves index.html for any non-API route
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # Never intercept API or docs routes — let them 404 naturally
            if full_path.startswith("api/") or full_path in ("openapi.json",):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            file_path = dist_dir / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(dist_dir / "index.html")

    return app


app = create_app()
