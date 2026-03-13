from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    # Register routers
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
        settings,
        snapshots,
        storyboard,
        timeline,
        tracks,
        users,
        video_clips,
        websockets,
    )

    app.include_router(auth.router)
    app.include_router(oauth.router)
    app.include_router(invites.router)
    app.include_router(users.router)
    app.include_router(projects.router)
    app.include_router(storyboard.router)
    app.include_router(keyframes.router)
    app.include_router(timeline.router)
    app.include_router(tracks.router)
    app.include_router(video_clips.router)
    app.include_router(audio_clips.router)
    app.include_router(assets.router)
    app.include_router(jobs.router)
    app.include_router(batches.router)
    app.include_router(model_registry.router)
    app.include_router(lora_registry.router)
    app.include_router(integrations.router)
    app.include_router(settings.router)
    app.include_router(snapshots.router)
    app.include_router(notifications.router)
    app.include_router(websockets.router)

    return app


app = create_app()
