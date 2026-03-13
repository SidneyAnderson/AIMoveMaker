"""Snapshot service — create, list, restore."""
import json
import os
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.snapshot import Snapshot

settings = get_settings()


async def list_snapshots(
    db: AsyncSession, project_id: str, skip: int = 0, limit: int = 100
) -> tuple[list[Snapshot], int]:
    count_result = await db.execute(
        select(func.count())
        .select_from(Snapshot)
        .where(Snapshot.project_id == project_id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.project_id == project_id)
        .order_by(Snapshot.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def create_snapshot(
    db: AsyncSession,
    project_id: str,
    user_id: str | None,
    snap_type: str = "manual",
    label: str | None = None,
) -> Snapshot:
    """Create a snapshot. For now, stores an empty JSON placeholder."""
    base = os.path.join(settings.STORAGE_BASE_PATH, "snapshots", project_id)
    subdir = "checkpoints" if snap_type == "checkpoint" else (
        "manual" if snap_type == "manual" else "auto"
    )
    snap_dir = os.path.join(base, subdir)
    os.makedirs(snap_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{ts}.json"
    path = os.path.join(snap_dir, filename)

    # Placeholder: full project export will be implemented per PRD spec
    snapshot_data = {"project_id": project_id, "type": snap_type, "created_at": ts}
    data_str = json.dumps(snapshot_data)
    with open(path, "w") as f:
        f.write(data_str)

    snapshot = Snapshot(
        project_id=project_id,
        type=snap_type,
        label=label,
        storage_path=path,
        size_bytes=len(data_str),
        created_by=user_id,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def restore_snapshot(db: AsyncSession, snapshot_id: str) -> None:
    """Restore a project to a snapshot state. Placeholder for now."""
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
    # Full restore logic will be implemented in integration phase
