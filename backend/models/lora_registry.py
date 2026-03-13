import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base

class LoRARegistry(Base):
    __tablename__ = "lora_registry"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    architecture: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hf_repo_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    civitai_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trigger_words: Mapped[list | None] = mapped_column(JSON, default=list, nullable=False)
    nsfw_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight_default: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    added_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
