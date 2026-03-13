import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(
        Enum(
            "draft",
            "creative_active",
            "pending_handoff",
            "eng_active",
            "pending_return",
            "completed",
            name="project_state_enum",
        ),
        default="draft",
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    global_negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_save_interval_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    resolution_w: Mapped[int] = mapped_column(Integer, default=1280, nullable=False)
    resolution_h: Mapped[int] = mapped_column(Integer, default=720, nullable=False)
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
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    storyboard = relationship("Storyboard", back_populates="project", uselist=False, cascade="all, delete-orphan")
    timeline = relationship("Timeline", back_populates="project", uselist=False, cascade="all, delete-orphan")
    handoffs = relationship("HandoffRecord", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="project", cascade="all, delete-orphan")
