"""Timeline, track, video clip, and audio clip schemas."""
from datetime import datetime

from pydantic import BaseModel


# --- Timeline ---

class TimelineUpdate(BaseModel):
    duration_ms: int | None = None
    fps: int | None = None
    resolution_w: int | None = None
    resolution_h: int | None = None


class TimelineResponse(BaseModel):
    id: str
    project_id: str
    duration_ms: int
    fps: int
    resolution_w: int
    resolution_h: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Tracks ---

class TrackCreate(BaseModel):
    type: str  # video, audio, controlnet
    name: str


class TrackUpdate(BaseModel):
    name: str | None = None
    order: int | None = None
    muted: bool | None = None
    locked: bool | None = None
    visible: bool | None = None


class TrackResponse(BaseModel):
    id: str
    timeline_id: str
    type: str
    name: str
    order: int
    muted: bool
    locked: bool
    visible: bool

    model_config = {"from_attributes": True}


class TrackListResponse(BaseModel):
    tracks: list[TrackResponse]
    total: int


# --- Video Clips ---

class VideoClipCreate(BaseModel):
    track_id: str
    start_ms: int
    end_ms: int
    source_asset_id: str | None = None
    mode: str = "i2v"
    model_id: str | None = None
    lora_stack: list | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    seed: int = -1
    frames: int | None = None
    fps: int | None = None
    motion_strength: float | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    params: dict | None = None
    cn_enabled: bool = False
    cn_type: str | None = None
    cn_control_asset_id: str | None = None
    cn_strength: float | None = None
    cn_start_pct: float | None = None
    cn_end_pct: float | None = None
    rife_enabled: bool = False
    rife_multiplier: str = "2x"
    scene_cut_detect: bool = True


class VideoClipUpdate(BaseModel):
    start_ms: int | None = None
    end_ms: int | None = None
    order: int | None = None
    source_asset_id: str | None = None
    mode: str | None = None
    model_id: str | None = None
    lora_stack: list | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    frames: int | None = None
    fps: int | None = None
    motion_strength: float | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    params: dict | None = None
    cn_enabled: bool | None = None
    cn_type: str | None = None
    cn_control_asset_id: str | None = None
    cn_strength: float | None = None
    cn_start_pct: float | None = None
    cn_end_pct: float | None = None
    rife_enabled: bool | None = None
    rife_multiplier: str | None = None
    scene_cut_detect: bool | None = None


class VideoClipResponse(BaseModel):
    id: str
    track_id: str
    start_ms: int
    end_ms: int
    order: int
    source_asset_id: str | None = None
    output_asset_id: str | None = None
    job_id: str | None = None
    render_state: str
    mode: str
    model_id: str | None = None
    lora_stack: list | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    seed: int
    frames: int | None = None
    fps: int | None = None
    motion_strength: float | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    params: dict | None = None
    cn_enabled: bool
    cn_type: str | None = None
    cn_control_asset_id: str | None = None
    cn_strength: float | None = None
    cn_start_pct: float | None = None
    cn_end_pct: float | None = None
    rife_enabled: bool
    rife_multiplier: str
    scene_cut_detect: bool
    interp_blend_mode: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoClipListResponse(BaseModel):
    video_clips: list[VideoClipResponse]
    total: int


# --- Audio Clips ---

class AudioClipCreate(BaseModel):
    track_id: str
    start_ms: int
    end_ms: int
    subtype: str  # music, sfx, tts, lipsync
    prompt: str | None = None
    model_id: str | None = None
    model_source: str = "local"
    api_provider: str | None = None
    params: dict | None = None
    volume: float = 1.0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    pan: float = 0.0
    loop: bool = False
    sync_to_asset_id: str | None = None
    sync_mode: str = "free"


class AudioClipUpdate(BaseModel):
    start_ms: int | None = None
    end_ms: int | None = None
    order: int | None = None
    subtype: str | None = None
    prompt: str | None = None
    model_id: str | None = None
    model_source: str | None = None
    api_provider: str | None = None
    params: dict | None = None
    volume: float | None = None
    fade_in_ms: int | None = None
    fade_out_ms: int | None = None
    pan: float | None = None
    loop: bool | None = None
    sync_to_asset_id: str | None = None
    sync_mode: str | None = None


class AudioClipResponse(BaseModel):
    id: str
    track_id: str
    start_ms: int
    end_ms: int
    order: int
    output_asset_id: str | None = None
    job_id: str | None = None
    render_state: str
    subtype: str
    prompt: str | None = None
    model_id: str | None = None
    model_source: str
    api_provider: str | None = None
    params: dict | None = None
    volume: float
    fade_in_ms: int
    fade_out_ms: int
    pan: float
    loop: bool
    sync_to_asset_id: str | None = None
    sync_mode: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AudioClipListResponse(BaseModel):
    audio_clips: list[AudioClipResponse]
    total: int
