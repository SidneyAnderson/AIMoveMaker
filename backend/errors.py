"""Central error code catalog for deeper, user-friendly error handling (gap #11).

Provides consistent error_code values + human-readable titles, messages, and suggested actions.
Used by generation tasks on failure and exposed to frontend for rich surfacing.
"""

from typing import TypedDict

class ErrorDetails(TypedDict):
    code: str
    title: str
    user_message: str
    suggested_action: str
    severity: str  # "error" | "warning"

# Centralized catalog - extend as new error paths are added
ERROR_CATALOG: dict[str, ErrorDetails] = {
    "image_generation_error": {
        "code": "image_generation_error",
        "title": "Image Generation Failed",
        "user_message": "The diffusion model failed to generate the image. This can happen with very complex prompts, unusual seeds, or temporary model loading issues.",
        "suggested_action": "Try a simpler prompt, lower resolution, different seed, or retry the job.",
        "severity": "error",
    },
    "video_generation_error": {
        "code": "video_generation_error",
        "title": "Video Generation Failed",
        "user_message": "Video model (LTX / WAN) encountered an error during generation. Common causes: high VRAM usage, long duration, or model-specific prompt issues.",
        "suggested_action": "Reduce frame count or resolution, remove heavy LoRAs/ControlNet, or try a different model.",
        "severity": "error",
    },
    "audio_generation_error": {
        "code": "audio_generation_error",
        "title": "Audio Generation Failed",
        "user_message": "MusicGen, AudioGen, or TTS pipeline failed. This often relates to prompt length, unsupported characters, or resource contention.",
        "suggested_action": "Shorten the prompt, split into multiple clips, or retry.",
        "severity": "error",
    },
    "interpolation_error": {
        "code": "interpolation_error",
        "title": "Frame Interpolation Failed",
        "user_message": "RIFE interpolation could not process the video. This can occur with very short clips or corrupted input frames.",
        "suggested_action": "Ensure the source video has enough frames and try again with lower interpolation factor.",
        "severity": "error",
    },
    "render_error": {
        "code": "render_error",
        "title": "Timeline Render Failed",
        "user_message": "FFmpeg render of the final timeline failed. Possible causes: missing assets, incompatible clip formats, or disk space issues.",
        "suggested_action": "Check that all assets in the timeline still exist, verify export settings, and retry.",
        "severity": "error",
    },
    "export_error": {
        "code": "export_error",
        "title": "Export Job Failed",
        "user_message": "The export (PNG sequence, EDL, or other) could not complete.",
        "suggested_action": "Verify input clips are valid and try exporting a smaller section first.",
        "severity": "error",
    },
    "model_load_error": {
        "code": "model_load_error",
        "title": "Model Failed to Load",
        "user_message": "The requested AI model could not be loaded into memory. This is often a VRAM or compatibility issue.",
        "suggested_action": "Check hardware profile, reduce concurrent jobs, or switch to a lighter model.",
        "severity": "error",
    },
    "oom_error": {
        "code": "oom_error",
        "title": "Out of Memory (VRAM)",
        "user_message": "The job exceeded available GPU memory. This is common with high-resolution video or stacked ControlNet + multiple LoRAs.",
        "suggested_action": "Lower resolution, reduce frames/LoRAs, or route the job to Vast.ai.",
        "severity": "error",
    },
    "ffmpeg_error": {
        "code": "ffmpeg_error",
        "title": "FFmpeg Processing Error",
        "user_message": "FFmpeg encountered a problem while processing video or audio (concat, scaling, encoding).",
        "suggested_action": "Ensure all source files are valid and not corrupted. Try a different export preset.",
        "severity": "error",
    },
}

DEFAULT_ERROR: ErrorDetails = {
    "code": "unknown_error",
    "title": "Unknown Error",
    "user_message": "An unexpected error occurred during processing.",
    "suggested_action": "Retry the job. If the problem persists, check the detailed logs.",
    "severity": "error",
}


def get_error_details(code: str | None, raw_msg: str | None = None) -> ErrorDetails:
    """Return rich, user-facing error information for a given code."""
    if not code:
        return {**DEFAULT_ERROR, "user_message": raw_msg or DEFAULT_ERROR["user_message"]}

    details = ERROR_CATALOG.get(code, DEFAULT_ERROR)
    if raw_msg and len(raw_msg) > 20:
        # Append a truncated raw hint for power users
        details = {**details, "user_message": f"{details['user_message']} (Technical: {raw_msg[:200]})"}
    return details


def get_all_error_codes() -> list[str]:
    return list(ERROR_CATALOG.keys())
