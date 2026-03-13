"""Project schemas."""
from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str | None = None
    fps: int = 24
    resolution_w: int = 1280
    resolution_h: int = 720
    global_negative_prompt: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    state: str | None = None
    fps: int | None = None
    resolution_w: int | None = None
    resolution_h: int | None = None
    global_negative_prompt: str | None = None
    auto_save_interval_s: int | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    state: str
    created_by: str
    global_negative_prompt: str | None = None
    auto_save_interval_s: int | None = None
    fps: int
    resolution_w: int
    resolution_h: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# --- Project Members ---

class ProjectMemberCreate(BaseModel):
    user_id: str
    role: str  # creative, engineer, viewer


class ProjectMemberResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    assigned_by: str
    assigned_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberListResponse(BaseModel):
    members: list[ProjectMemberResponse]
    total: int


# --- Handoffs ---

class HandoffCreate(BaseModel):
    direction: str  # creative_to_eng, eng_to_creative
    notes: str | None = None


class HandoffResponse(BaseModel):
    id: str
    project_id: str
    direction: str
    initiated_by: str
    accepted_by: str | None = None
    initiated_at: datetime
    accepted_at: datetime | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class HandoffListResponse(BaseModel):
    handoffs: list[HandoffResponse]
    total: int
