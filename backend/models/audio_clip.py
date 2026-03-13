import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

class AudioClip(Base):
    __tablename__ = "audio_clips"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    track_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    output_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=True
    )
    render_state: Mapped[str] = mapped_column(
        Enum("unrendered", "rendering", "done", "error", name="render_state_enum", create_constraint=False),
        default="unrendered",
        nullable=False,
    )
    subtype: Mapped[str] = mapped_column(
        Enum("music", "sfx", "tts", "lipsync", name="audio_subtype_enum"),
        nullable=False,
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_registry.id"), nullable=True
    )
    model_source: Mapped[str] = mapped_column(
        Enum("local", "api", name="model_source_enum"), default="local", nullable=False
    )
    api_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    fade_in_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fade_out_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pan: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    loop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sync_to_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    sync_mode: Mapped[str] = mapped_column(
        Enum("free", "locked", name="sync_mode_enum"), default="free", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    track = relationship("Track", back_populates="audio_clips")
    model = relationship("ModelRegistry", foreign_keys=[model_id])
