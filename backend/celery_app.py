"""Celery application configuration."""
from celery import Celery

from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "aimoviemaker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Priority queuing
    task_default_queue="default",
    task_queues={
        "high": {"exchange": "high", "routing_key": "high"},
        "medium": {"exchange": "medium", "routing_key": "medium"},
        "default": {"exchange": "default", "routing_key": "default"},
        "low": {"exchange": "low", "routing_key": "low"},
    },
    task_default_priority=5,
    task_queue_max_priority=10,
)

# Auto-discover task modules
celery_app.autodiscover_tasks(["backend.tasks"])
