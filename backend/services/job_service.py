"""Job and batch service — CRUD, dispatch, VRAM gating."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.batch import Batch
from backend.models.job import Job
from backend.models.model_registry import ModelRegistry


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

async def list_jobs(
    db: AsyncSession,
    project_id: str | None = None,
    status_filter: str | None = None,
    type_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Job], int]:
    q = select(Job)
    cq = select(func.count()).select_from(Job)

    if project_id:
        q = q.where(Job.project_id == project_id)
        cq = cq.where(Job.project_id == project_id)
    if status_filter:
        q = q.where(Job.status == status_filter)
        cq = cq.where(Job.status == status_filter)
    if type_filter:
        q = q.where(Job.type == type_filter)
        cq = cq.where(Job.type == type_filter)

    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(
        q.order_by(Job.queued_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def create_job(db: AsyncSession, user_id: str, data: dict) -> Job:
    """Create a job with VRAM profiling and dispatch to Celery."""
    # VRAM profiling gate (per PRD §6.1.3)
    model_id = data.get("model_id")
    vram_estimate = None
    if model_id:
        result = await db.execute(
            select(ModelRegistry).where(ModelRegistry.id == model_id)
        )
        model = result.scalar_one_or_none()
        if model:
            try:
                from backend.hardware_profile import estimate_vram_mb, check_vram_sufficient

                vram_estimate = estimate_vram_mb(
                    model_vram_floor_mb=model.vram_floor_mb,
                    width=data.get("width", 512),
                    height=data.get("height", 512),
                    frames=data.get("frames", 1),
                    lora_count=len(data.get("lora_stack", [])),
                )
                data["vram_estimate_mb"] = vram_estimate

                is_sufficient, vram_info = check_vram_sufficient(vram_estimate)
                if not is_sufficient:
                    # Flag for Vast.ai routing — frontend must show confirmation
                    data["gpu_target"] = "vastai"
            except Exception:
                pass  # Hardware profile unavailable, proceed with local

    job = Job(user_id=user_id, **data)
    db.add(job)
    await db.flush()

    # Dispatch to Celery queue
    try:
        from backend.tasks.generation_tasks import TASK_REGISTRY, _get_queue

        task_name = TASK_REGISTRY.get(job.type)
        if task_name:
            from backend.celery_app import celery_app
            queue = _get_queue(job.priority)
            celery_app.send_task(
                task_name,
                args=[job.id, data],
                queue=queue,
            )
    except Exception:
        pass  # Celery not available (e.g., tests)

    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job


async def cancel_job(db: AsyncSession, job_id: str, user_id: str, is_admin: bool) -> None:
    job = await get_job(db, job_id)

    if job.status not in ("queued", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status}'",
        )
    if not is_admin and job.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only cancel your own jobs",
        )

    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------

async def list_batches(
    db: AsyncSession,
    project_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Batch], int]:
    q = select(Batch)
    cq = select(func.count()).select_from(Batch)
    if project_id:
        q = q.where(Batch.project_id == project_id)
        cq = cq.where(Batch.project_id == project_id)
    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(
        q.order_by(Batch.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def create_batch(
    db: AsyncSession, user_id: str, project_id: str, name: str, job_ids: list[str]
) -> Batch:
    batch = Batch(
        project_id=project_id,
        name=name,
        created_by=user_id,
        job_count=len(job_ids),
    )
    db.add(batch)
    await db.flush()

    # Link jobs to batch
    if job_ids:
        result = await db.execute(select(Job).where(Job.id.in_(job_ids)))
        for job in result.scalars().all():
            job.batch_id = batch.id
        await db.flush()

    return batch


async def get_batch(db: AsyncSession, batch_id: str) -> Batch:
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found"
        )
    return batch
