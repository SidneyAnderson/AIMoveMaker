"""Job and batch schemas."""
from datetime import datetime

from pydantic import BaseModel


class JobCreate(BaseModel):
    project_id: str
    type: str  # image_generation, video_generation, etc.
    source_entity_type: str  # keyframe, videoclip, audioclip, project
    source_entity_id: str
    priority: str = "normal"
    gpu_target: str = "local"
    user_ack: bool = False


class JobResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    batch_id: str | None = None
    type: str
    source_entity_type: str
    source_entity_id: str
    status: str
    priority: str
    queue_position: int | None = None
    gpu_target: str
    vastai_instance_id: str | None = None
    vram_estimate_mb: int | None = None
    vram_actual_mb: int | None = None
    cost_estimate_usd: float | None = None
    cost_actual_usd: float | None = None
    user_ack: bool
    user_ack_at: datetime | None = None
    ack_by: str | None = None
    progress_pct: int
    current_step: int | None = None
    total_steps: int | None = None
    eta_seconds: int | None = None
    retry_count: int
    max_retries: int
    error_code: str | None = None
    error_msg: str | None = None
    log_stream_id: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


# --- Batches ---

class BatchCreate(BaseModel):
    project_id: str
    name: str
    job_ids: list[str] = []


class BatchResponse(BaseModel):
    id: str
    project_id: str
    name: str
    created_by: str
    created_at: datetime
    job_count: int
    done_count: int
    failed_count: int
    status: str

    model_config = {"from_attributes": True}


class BatchListResponse(BaseModel):
    batches: list[BatchResponse]
    total: int
