import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base

class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("image", "video", "audio", name="model_type_enum"), nullable=False
    )
    architecture: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vram_floor_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    vram_recommended_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    supports_cpu_offload: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_fp8: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_fp16: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_compute_capability: Mapped[str | None] = mapped_column(String(10), nullable=True)
    param_schema: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=False)
    compatible_lora_architectures: Mapped[list | None] = mapped_column(
        JSON, default=list, nullable=False
    )
    lora_weight_min: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    lora_weight_max: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    max_lora_stack_size: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hf_repo_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    civitai_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
