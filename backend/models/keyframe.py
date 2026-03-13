import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

class Keyframe(Base):
    __tablename__ = "keyframes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    storyboard_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    neg_prompt_scope: Mapped[str] = mapped_column(
        Enum("keyframe", "global", name="neg_prompt_scope_enum"),
        default="global",
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(
        Enum("t2i", "i2i", "inpaint", "outpaint", name="keyframe_mode_enum"),
        default="t2i",
        nullable=False,
    )
    seed: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    seed_mode: Mapped[str] = mapped_column(
        Enum("fixed", "random", "variation", name="seed_mode_enum"),
        default="random",
        nullable=False,
    )
    variation_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_registry.id"), nullable=True
    )
    lora_stack: Mapped[list | None] = mapped_column(JSON, default=list, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=False)

    # ControlNet fields
    cn_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cn_type: Mapped[str | None] = mapped_column(
        Enum("depth", "canny", "pose", "reference", name="cn_type_enum"),
        nullable=True,
    )
    cn_control_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    cn_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    cn_start_pct: Mapped[float | None] = mapped_column(Float, default=0.0, nullable=True)
    cn_end_pct: Mapped[float | None] = mapped_column(Float, default=1.0, nullable=True)

    # Asset references
    selected_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True
    )
    candidate_asset_ids: Mapped[list | None] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
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
    storyboard = relationship("Storyboard", back_populates="keyframes")
    model = relationship("ModelRegistry", foreign_keys=[model_id])
