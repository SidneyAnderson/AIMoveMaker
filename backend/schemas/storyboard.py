"""Storyboard and keyframe schemas."""
from datetime import datetime

from pydantic import BaseModel


class StoryboardResponse(BaseModel):
    id: str
    project_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoryboardReorderRequest(BaseModel):
    keyframe_ids: list[str]  # ordered list of keyframe IDs


# --- Keyframes ---

class KeyframeCreate(BaseModel):
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    neg_prompt_scope: str = "global"
    mode: str = "t2i"
    seed: int = -1
    seed_mode: str = "random"
    variation_count: int = 1
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    cn_enabled: bool = False
    cn_type: str | None = None
    cn_control_asset_id: str | None = None
    cn_strength: float | None = None
    cn_start_pct: float | None = None
    cn_end_pct: float | None = None
    insert_after: str | None = None  # keyframe ID to insert after


class KeyframeUpdate(BaseModel):
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    neg_prompt_scope: str | None = None
    mode: str | None = None
    seed: int | None = None
    seed_mode: str | None = None
    variation_count: int | None = None
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    cn_enabled: bool | None = None
    cn_type: str | None = None
    cn_control_asset_id: str | None = None
    cn_strength: float | None = None
    cn_start_pct: float | None = None
    cn_end_pct: float | None = None
    selected_asset_id: str | None = None


class KeyframeResponse(BaseModel):
    id: str
    storyboard_id: str
    index: int
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    neg_prompt_scope: str
    mode: str
    seed: int
    seed_mode: str
    variation_count: int
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    cn_enabled: bool
    cn_type: str | None = None
    cn_control_asset_id: str | None = None
    cn_strength: float | None = None
    cn_start_pct: float | None = None
    cn_end_pct: float | None = None
    selected_asset_id: str | None = None
    candidate_asset_ids: list | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KeyframeListResponse(BaseModel):
    keyframes: list[KeyframeResponse]
    total: int
