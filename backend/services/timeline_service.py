"""Timeline, track, video clip, and audio clip service."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audio_clip import AudioClip
from backend.models.timeline import Timeline
from backend.models.track import Track
from backend.models.video_clip import VideoClip


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

async def get_timeline(db: AsyncSession, project_id: str) -> Timeline:
    result = await db.execute(
        select(Timeline).where(Timeline.project_id == project_id)
    )
    timeline = result.scalar_one_or_none()
    if timeline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline not found for this project",
        )
    return timeline


async def update_timeline(db: AsyncSession, project_id: str, data: dict) -> Timeline:
    timeline = await get_timeline(db, project_id)
    for key, value in data.items():
        if value is not None and hasattr(timeline, key):
            setattr(timeline, key, value)
    await db.flush()
    return timeline


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

async def list_tracks(db: AsyncSession, project_id: str) -> tuple[list[Track], int]:
    timeline = await get_timeline(db, project_id)
    result = await db.execute(
        select(Track)
        .where(Track.timeline_id == timeline.id)
        .order_by(Track.order)
    )
    tracks = list(result.scalars().all())
    return tracks, len(tracks)


async def create_track(
    db: AsyncSession, project_id: str, track_type: str, name: str
) -> Track:
    timeline = await get_timeline(db, project_id)

    # Get next order
    result = await db.execute(
        select(func.max(Track.order)).where(Track.timeline_id == timeline.id)
    )
    max_order = result.scalar() or -1

    track = Track(
        timeline_id=timeline.id,
        type=track_type,
        name=name,
        order=max_order + 1,
    )
    db.add(track)
    await db.flush()
    return track


async def get_track(db: AsyncSession, track_id: str) -> Track:
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found"
        )
    return track


async def update_track(db: AsyncSession, track_id: str, data: dict) -> Track:
    track = await get_track(db, track_id)
    for key, value in data.items():
        if value is not None and hasattr(track, key):
            setattr(track, key, value)
    await db.flush()
    return track


async def delete_track(db: AsyncSession, track_id: str) -> None:
    track = await get_track(db, track_id)
    await db.delete(track)
    await db.flush()


# ---------------------------------------------------------------------------
# Video Clips
# ---------------------------------------------------------------------------

async def list_video_clips(
    db: AsyncSession, project_id: str
) -> tuple[list[VideoClip], int]:
    timeline = await get_timeline(db, project_id)
    result = await db.execute(
        select(VideoClip)
        .join(Track, Track.id == VideoClip.track_id)
        .where(Track.timeline_id == timeline.id)
        .order_by(VideoClip.order)
    )
    clips = list(result.scalars().all())
    return clips, len(clips)


async def create_video_clip(db: AsyncSession, data: dict) -> VideoClip:
    # Verify track exists and is video type
    track = await get_track(db, data["track_id"])
    if track.type != "video":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track must be of type 'video'",
        )

    # Get next order
    result = await db.execute(
        select(func.max(VideoClip.order)).where(VideoClip.track_id == track.id)
    )
    max_order = result.scalar() or -1

    clip = VideoClip(order=max_order + 1, **data)
    db.add(clip)

    # Auto-extend timeline duration
    tl_result = await db.execute(
        select(Timeline).where(Timeline.id == track.timeline_id)
    )
    timeline = tl_result.scalar_one()
    if clip.end_ms > timeline.duration_ms:
        timeline.duration_ms = clip.end_ms

    await db.flush()
    return clip


async def get_video_clip(db: AsyncSession, clip_id: str) -> VideoClip:
    result = await db.execute(select(VideoClip).where(VideoClip.id == clip_id))
    clip = result.scalar_one_or_none()
    if clip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video clip not found"
        )
    return clip


async def update_video_clip(db: AsyncSession, clip_id: str, data: dict) -> VideoClip:
    clip = await get_video_clip(db, clip_id)
    for key, value in data.items():
        if value is not None and hasattr(clip, key):
            setattr(clip, key, value)
    await db.flush()
    return clip


async def delete_video_clip(db: AsyncSession, clip_id: str) -> None:
    clip = await get_video_clip(db, clip_id)
    await db.delete(clip)
    await db.flush()


# ---------------------------------------------------------------------------
# Audio Clips
# ---------------------------------------------------------------------------

async def list_audio_clips(
    db: AsyncSession, project_id: str
) -> tuple[list[AudioClip], int]:
    timeline = await get_timeline(db, project_id)
    result = await db.execute(
        select(AudioClip)
        .join(Track, Track.id == AudioClip.track_id)
        .where(Track.timeline_id == timeline.id)
        .order_by(AudioClip.order)
    )
    clips = list(result.scalars().all())
    return clips, len(clips)


async def create_audio_clip(db: AsyncSession, data: dict) -> AudioClip:
    track = await get_track(db, data["track_id"])
    if track.type != "audio":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track must be of type 'audio'",
        )

    result = await db.execute(
        select(func.max(AudioClip.order)).where(AudioClip.track_id == track.id)
    )
    max_order = result.scalar() or -1

    clip = AudioClip(order=max_order + 1, **data)
    db.add(clip)

    # Auto-extend timeline duration
    tl_result = await db.execute(
        select(Timeline).where(Timeline.id == track.timeline_id)
    )
    timeline = tl_result.scalar_one()
    if clip.end_ms > timeline.duration_ms:
        timeline.duration_ms = clip.end_ms

    await db.flush()
    return clip


async def get_audio_clip(db: AsyncSession, clip_id: str) -> AudioClip:
    result = await db.execute(select(AudioClip).where(AudioClip.id == clip_id))
    clip = result.scalar_one_or_none()
    if clip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio clip not found"
        )
    return clip


async def update_audio_clip(db: AsyncSession, clip_id: str, data: dict) -> AudioClip:
    clip = await get_audio_clip(db, clip_id)
    for key, value in data.items():
        if value is not None and hasattr(clip, key):
            setattr(clip, key, value)
    await db.flush()
    return clip


async def delete_audio_clip(db: AsyncSession, clip_id: str) -> None:
    clip = await get_audio_clip(db, clip_id)
    await db.delete(clip)
    await db.flush()
