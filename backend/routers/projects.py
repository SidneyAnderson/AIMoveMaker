"""Projects router — CRUD + members + handoffs with auth."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_active_user, require_admin
from backend.models.user import User
from backend.schemas.common import MessageResponse
from backend.schemas.projects import (
    HandoffCreate,
    HandoffListResponse,
    HandoffResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from backend.services.project_service import (
    accept_handoff,
    add_member,
    create_handoff,
    create_project,
    decline_handoff,
    delete_project,
    get_project,
    list_handoffs,
    list_members,
    list_projects,
    remove_member,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=ProjectListResponse)
async def list_projects_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    projects, total = await list_projects(db, current_user, skip=skip, limit=limit)
    return ProjectListResponse(projects=projects, total=total)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    body: ProjectCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await create_project(db, admin.id, body.model_dump())
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project_endpoint(
    project_id: str,
    body: ProjectUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await get_project(db, project_id)
    return await update_project(db, project, body.model_dump(exclude_unset=True), is_admin=True)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_endpoint(
    project_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_project(db, project_id)
    return None


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
async def list_members_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    members, total = await list_members(db, project_id)
    return ProjectMemberListResponse(members=members, total=total)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member_endpoint(
    project_id: str,
    body: ProjectMemberCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    member = await add_member(db, project_id, body.user_id, body.role, admin.id)
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_endpoint(
    project_id: str,
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await remove_member(db, project_id, user_id)
    return None


@router.get("/{project_id}/handoffs", response_model=HandoffListResponse)
async def list_handoffs_endpoint(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    handoffs, total = await list_handoffs(db, project_id)
    return HandoffListResponse(handoffs=handoffs, total=total)


@router.post(
    "/{project_id}/handoffs",
    response_model=HandoffResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_handoff_endpoint(
    project_id: str,
    body: HandoffCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    handoff = await create_handoff(db, project_id, current_user.id, body.direction, body.notes)
    return handoff


@router.patch("/{project_id}/handoffs/{handoff_id}/accept", response_model=HandoffResponse)
async def accept_handoff_endpoint(
    project_id: str,
    handoff_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await accept_handoff(db, handoff_id, current_user.id)


@router.patch("/{project_id}/handoffs/{handoff_id}/decline", response_model=MessageResponse)
async def decline_handoff_endpoint(
    project_id: str,
    handoff_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await decline_handoff(db, handoff_id)
    return MessageResponse(message="Handoff declined")
