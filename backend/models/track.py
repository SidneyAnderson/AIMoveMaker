import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("timelines.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        Enum("video", "audio", "controlnet", name="track_type_enum"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    timeline = relationship("Timeline", back_populates="tracks")
    video_clips = relationship("VideoClip", back_populates="track", cascade="all, delete-orphan")
    audio_clips = relationship("AudioClip", back_populates="track", cascade="all, delete-orphan")
