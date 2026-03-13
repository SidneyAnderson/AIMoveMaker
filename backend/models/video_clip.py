import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

class VideoClip(Base):
    __tablename__ = "video_clips"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    track_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    output_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=True
    )
    render_state: Mapped[str] = mapped_column(
        Enum("unrendered", "rendering", "done", "error", name="render_state_enum"),
        default="unrendered",
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(
        Enum("t2v", "i2v", "v2v", name="video_mode_enum"),
        default="i2v",
        nullable=False,
    )
    model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_registry.id"), nullable=True
    )
    lora_stack: Mapped[list | None] = mapped_column(JSON, default=list, nullable=False)
    positive_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motion_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cfg_scale: Mapped[float | None] = mapped_column(Float, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=False)

    # ControlNet
    cn_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cn_type: Mapped[str | None] = mapped_column(
        Enum("depth", "canny", "pose", "reference", name="cn_type_enum", create_constraint=False),
        nullable=True,
    )
    cn_control_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    cn_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    cn_start_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cn_end_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # RIFE
    rife_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rife_multiplier: Mapped[str] = mapped_column(
        Enum("2x", "4x", name="rife_multiplier_enum"), default="2x", nullable=False
    )
    scene_cut_detect: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interp_blend_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)

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
    track = relationship("Track", back_populates="video_clips")
    model = relationship("ModelRegistry", foreign_keys=[model_id])
