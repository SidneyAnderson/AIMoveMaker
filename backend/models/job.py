import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    batch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("batches.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(
        Enum(
            "image_generation", "video_generation", "audio_generation",
            "interpolation", "inpaint", "outpaint", "render", "export",
            name="job_type_enum",
        ),
        nullable=False,
    )
    source_entity_type: Mapped[str] = mapped_column(
        Enum("keyframe", "videoclip", "audioclip", "project", name="source_entity_type_enum"),
        nullable=False,
    )
    source_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("queued", "running", "done", "failed", "cancelled", name="job_status_enum"),
        default="queued",
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        Enum("high", "medium", "normal", "low", name="job_priority_enum"),
        default="normal",
        nullable=False,
    )
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gpu_target: Mapped[str] = mapped_column(
        Enum("local", "vastai", name="gpu_target_enum"), default="local", nullable=False
    )
    vastai_instance_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vram_estimate_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vram_actual_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate_usd: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    cost_actual_usd: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    user_ack: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_ack_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ack_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_stream_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    batch = relationship("Batch", back_populates="jobs")
