"""Snapshot service — create, list, restore project state."""
import json
import os
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.keyframe import Keyframe
from backend.models.snapshot import Snapshot
from backend.models.storyboard import Storyboard
from backend.models.timeline import Timeline
from backend.models.track import Track
from backend.models.video_clip import VideoClip
from backend.models.audio_clip import AudioClip
from backend.models.project import Project

settings = get_settings()


async def list_snapshots(
    db: AsyncSession, project_id: str, tier: str | None = None, skip: int = 0, limit: int = 100
) -> tuple[list[Snapshot], int]:
    q = select(Snapshot).where(Snapshot.project_id == project_id)
    cq = select(func.count()).select_from(Snapshot).where(Snapshot.project_id == project_id)
    if tier:
        q = q.where(Snapshot.tier == tier)
        cq = cq.where(Snapshot.tier == tier)
    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(
        q.order_by(Snapshot.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


def _row_to_dict(obj: object, keys: list[str]) -> dict:
    """Extract specified attributes from a model into a serializable dict."""
    d = {}
    for k in keys:
        v = getattr(obj, k, None)
        if isinstance(v, datetime):
            v = v.isoformat()
        d[k] = v
    return d


async def create_snapshot(
    db: AsyncSession,
    project_id: str,
    user_id: str | None,
    snap_type: str = "manual",
    tier: str = "manual",
    label: str | None = None,
) -> Snapshot:
    """Create a tiered snapshot (auto, manual, major, handoff) with auto-versioning."""
    base = os.path.join(settings.STORAGE_BASE_PATH, "snapshots", project_id)
    subdir = "checkpoints" if snap_type == "checkpoint" else (
        "manual" if snap_type == "manual" else "auto"
    )
    snap_dir = os.path.join(base, subdir)
    os.makedirs(snap_dir, exist_ok=True)

    # Auto-versioning: count existing for tier
    count_result = await db.execute(
        select(func.count(Snapshot.id)).where(
            Snapshot.project_id == project_id,
            Snapshot.tier == tier
        )
    )
    version = (count_result.scalar() or 0) + 1
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{tier}_v{version}_{ts}.json"
    path = os.path.join(snap_dir, filename)

    auto_label = label or f"{tier.title()} {snap_type} v{version} ({ts})"

    # Serialize project state
    # 1. Storyboard + keyframes
    sb_result = await db.execute(
        select(Storyboard).where(Storyboard.project_id == project_id)
    )
    storyboard = sb_result.scalar_one_or_none()

    keyframes_data = []
    if storyboard:
        kf_result = await db.execute(
            select(Keyframe)
            .where(Keyframe.storyboard_id == storyboard.id)
            .order_by(Keyframe.index)
        )
        for kf in kf_result.scalars().all():
            keyframes_data.append(_row_to_dict(kf, [
                "id", "storyboard_id", "index", "positive_prompt", "negative_prompt",
                "neg_prompt_scope", "mode", "seed", "seed_mode", "model_id",
                "variation_count", "cn_enabled", "cn_type", "cn_strength",
                "cn_start_pct", "cn_end_pct", "selected_asset_id",
            ]))

    # 2. Timeline + tracks + clips
    tl_result = await db.execute(
        select(Timeline).where(Timeline.project_id == project_id)
    )
    timeline = tl_result.scalar_one_or_none()

    tracks_data = []
    video_clips_data = []
    audio_clips_data = []
    if timeline:
        tr_result = await db.execute(
            select(Track).where(Track.timeline_id == timeline.id).order_by(Track.order)
        )
        for tr in tr_result.scalars().all():
            tracks_data.append(_row_to_dict(tr, [
                "id", "timeline_id", "name", "type", "order", "locked", "visible", "muted",
            ]))

        # Collect track IDs to query clips
        track_ids = [t["id"] for t in tracks_data]

        if track_ids:
            vc_result = await db.execute(
                select(VideoClip).where(VideoClip.track_id.in_(track_ids))
            )
            for vc in vc_result.scalars().all():
                video_clips_data.append(_row_to_dict(vc, [
                    "id", "track_id", "start_ms", "end_ms", "order",
                    "source_asset_id", "output_asset_id", "render_state",
                    "mode", "positive_prompt", "negative_prompt", "seed",
                ]))

            ac_result = await db.execute(
                select(AudioClip).where(AudioClip.track_id.in_(track_ids))
            )
            for ac in ac_result.scalars().all():
                audio_clips_data.append(_row_to_dict(ac, [
                    "id", "track_id", "start_ms", "end_ms", "order",
                    "output_asset_id", "render_state", "subtype", "prompt",
                    "volume", "fade_in_ms", "fade_out_ms",
                ]))

    snapshot_data = {
        "project_id": project_id,
        "type": snap_type,
        "created_at": ts,
        "storyboard_id": storyboard.id if storyboard else None,
        "keyframes": keyframes_data,
        "timeline_id": timeline.id if timeline else None,
        "timeline_duration_ms": timeline.duration_ms if timeline else 0,
        "tracks": tracks_data,
        "video_clips": video_clips_data,
        "audio_clips": audio_clips_data,
    }

    data_str = json.dumps(snapshot_data, indent=2, default=str)
    with open(path, "w") as f:
        f.write(data_str)

    snapshot = Snapshot(
        project_id=project_id,
        type=snap_type,
        tier=tier,
        label=auto_label,
        storage_path=path,
        size_bytes=len(data_str),
        created_by=user_id,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def restore_snapshot(db: AsyncSession, snapshot_id: str) -> None:
    """Restore a project to a snapshot state.

    Replaces keyframes, tracks, and clips with the snapshot data.
    """
    result = await db.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found"
        )
    if not os.path.exists(snapshot.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot file not found on disk",
        )

    with open(snapshot.storage_path) as f:
        data = json.load(f)

    project_id = data["project_id"]

    # Restore keyframes
    storyboard_id = data.get("storyboard_id")
    if storyboard_id:
        # Delete existing keyframes
        await db.execute(
            delete(Keyframe).where(Keyframe.storyboard_id == storyboard_id)
        )
        # Re-create from snapshot
        for kf_data in data.get("keyframes", []):
            kf = Keyframe(**{k: v for k, v in kf_data.items() if v is not None})
            db.add(kf)

    # Restore timeline clips
    timeline_id = data.get("timeline_id")
    if timeline_id:
        # Delete existing clips and tracks
        await db.execute(
            delete(VideoClip).where(VideoClip.timeline_id == timeline_id)
        )
        await db.execute(
            delete(AudioClip).where(AudioClip.timeline_id == timeline_id)
        )
        await db.execute(
            delete(Track).where(Track.timeline_id == timeline_id)
        )

        # Update timeline duration
        tl_result = await db.execute(
            select(Timeline).where(Timeline.id == timeline_id)
        )
        tl = tl_result.scalar_one_or_none()
        if tl:
            tl.duration_ms = data.get("timeline_duration_ms", 0)

        # Re-create tracks
        for tr_data in data.get("tracks", []):
            tr = Track(**{k: v for k, v in tr_data.items() if v is not None})
            db.add(tr)

        # Re-create clips
        for vc_data in data.get("video_clips", []):
            vc = VideoClip(**{k: v for k, v in vc_data.items() if v is not None})
            db.add(vc)

        for ac_data in data.get("audio_clips", []):
            ac = AudioClip(**{k: v for k, v in ac_data.items() if v is not None})
            db.add(ac)

    await db.flush()
