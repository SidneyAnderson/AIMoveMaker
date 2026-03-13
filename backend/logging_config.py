"""Logging configuration with loguru — file rotation, structured output.

Configures:
  - Console sink: colorized, INFO+ (or LOG_LEVEL from env)
  - File sink: logs/app.log with rotation (50 MB / 7 days), 30-day retention
  - JSON file sink: logs/app.json for structured log aggregation
"""
import sys
from pathlib import Path

from loguru import logger

from backend.config import get_settings


def configure_logging() -> None:
    """Configure loguru sinks with rotation. Call once at app startup."""
    settings = get_settings()
    log_level = settings.LOG_LEVEL.upper()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Remove default loguru handler
    logger.remove()

    # ── Console sink ─────────────────────────────────────────────────
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=(settings.ENVIRONMENT == "development"),
    )

    # ── Rotating file sink (human-readable) ──────────────────────────
    logger.add(
        str(log_dir / "app.log"),
        level=log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} — {message}"
        ),
        rotation="50 MB",       # Rotate when file reaches 50 MB
        retention="30 days",    # Keep logs for 30 days
        compression="gz",       # Compress rotated logs
        backtrace=True,
        diagnose=False,         # Never include variable values in file logs
        encoding="utf-8",
    )

    # ── JSON file sink (structured, for log aggregation) ─────────────
    logger.add(
        str(log_dir / "app.json"),
        level=log_level,
        format="{message}",
        serialize=True,         # JSON serialization
        rotation="50 MB",
        retention="14 days",
        compression="gz",
        encoding="utf-8",
    )

    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_dir": str(log_dir.resolve()),
            "environment": settings.ENVIRONMENT,
        },
    )
