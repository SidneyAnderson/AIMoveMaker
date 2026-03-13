"""Jobs router with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models.user import User
from backend.schemas.jobs import JobCreate, JobListResponse, JobResponse
from backend.services.job_service import cancel_job, create_job, get_job, list_jobs

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", response_model=JobListResponse)
async def list_jobs_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = None,
    status_filter: str | None = None,
    type_filter: str | None = None,
):
    jobs, total = await list_jobs(db, project_id=project_id, status_filter=status_filter, type_filter=type_filter)
    return JobListResponse(jobs=jobs, total=total)


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_endpoint(
    body: JobCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_job(db, current_user.id, body.model_dump())


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_endpoint(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_job(db, job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job_endpoint(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await cancel_job(db, job_id, current_user.id, is_admin=(current_user.global_role == "admin"))
    return None
