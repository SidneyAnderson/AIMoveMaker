"""Project service — CRUD, members, handoffs, state machine."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.handoff_record import HandoffRecord
from backend.models.notification import Notification
from backend.models.project import Project
from backend.models.project_member import ProjectMember
from backend.models.storyboard import Storyboard
from backend.models.timeline import Timeline
from backend.models.user import User


# ---------------------------------------------------------------------------
# State machine transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS = {
    "draft": ["creative_active"],
    "creative_active": ["pending_handoff"],
    "pending_handoff": ["creative_active", "eng_active"],
    "eng_active": ["pending_return", "completed"],
    "pending_return": ["creative_active", "eng_active"],
    "completed": ["draft"],  # admin reopen
}


def validate_state_transition(current: str, target: str, is_admin: bool) -> None:
    if is_admin:
        return  # Admin MAY force any state transition
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current}' to '{target}'",
        )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

async def list_projects(
    db: AsyncSession, user: User, skip: int = 0, limit: int = 100
) -> tuple[list[Project], int]:
    """List projects the user has access to. Admin sees all."""
    if user.global_role == "admin":
        q = select(Project)
        cq = select(func.count()).select_from(Project)
    else:
        q = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user.id)
        )
        cq = (
            select(func.count())
            .select_from(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user.id)
        )
    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(q.order_by(Project.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def create_project(db: AsyncSession, admin_id: str, data: dict) -> Project:
    project = Project(created_by=admin_id, **data)
    db.add(project)
    await db.flush()

    # Auto-create storyboard and timeline per PRD (one per project)
    storyboard = Storyboard(project_id=project.id, created_by=admin_id)
    timeline = Timeline(
        project_id=project.id,
        fps=project.fps,
        resolution_w=project.resolution_w,
        resolution_h=project.resolution_h,
    )
    db.add(storyboard)
    db.add(timeline)
    await db.flush()
    return project


async def get_project(db: AsyncSession, project_id: str) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def update_project(db: AsyncSession, project: Project, data: dict, is_admin: bool) -> Project:
    if "state" in data and data["state"] is not None:
        validate_state_transition(project.state, data["state"], is_admin)
    for key, value in data.items():
        if value is not None and hasattr(project, key):
            setattr(project, key, value)
    await db.flush()
    return project


async def delete_project(db: AsyncSession, project_id: str) -> None:
    project = await get_project(db, project_id)
    await db.delete(project)
    await db.flush()


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

async def list_members(
    db: AsyncSession, project_id: str
) -> tuple[list[ProjectMember], int]:
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    members = list(result.scalars().all())
    return members, len(members)


async def add_member(
    db: AsyncSession, project_id: str, user_id: str, role: str, admin_id: str
) -> ProjectMember:
    # Verify project exists
    await get_project(db, project_id)

    # Check role constraints: exactly 1 creative, exactly 1 engineer per project
    if role in ("creative", "engineer"):
        existing = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == role,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project already has a {role} assigned",
            )

    # Check user not already a member
    dup = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this project",
        )

    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        assigned_by=admin_id,
    )
    db.add(member)
    await db.flush()
    return member


async def remove_member(db: AsyncSession, project_id: str, user_id: str) -> None:
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    await db.delete(member)
    await db.flush()


# ---------------------------------------------------------------------------
# Handoffs
# ---------------------------------------------------------------------------

async def list_handoffs(
    db: AsyncSession, project_id: str
) -> tuple[list[HandoffRecord], int]:
    result = await db.execute(
        select(HandoffRecord)
        .where(HandoffRecord.project_id == project_id)
        .order_by(HandoffRecord.initiated_at.desc())
    )
    handoffs = list(result.scalars().all())
    return handoffs, len(handoffs)


async def create_handoff(
    db: AsyncSession, project_id: str, user_id: str, direction: str, notes: str | None
) -> HandoffRecord:
    project = await get_project(db, project_id)

    # Validate direction against current state
    if direction == "creative_to_eng" and project.state != "creative_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project must be in 'creative_active' state to submit handoff",
        )
    if direction == "eng_to_creative" and project.state != "eng_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project must be in 'eng_active' state to request return",
        )

    handoff = HandoffRecord(
        project_id=project_id,
        direction=direction,
        initiated_by=user_id,
        notes=notes,
    )
    db.add(handoff)

    # Transition state
    if direction == "creative_to_eng":
        project.state = "pending_handoff"
    else:
        project.state = "pending_return"

    await db.flush()
    return handoff


async def accept_handoff(db: AsyncSession, handoff_id: str, user_id: str) -> HandoffRecord:
    result = await db.execute(select(HandoffRecord).where(HandoffRecord.id == handoff_id))
    handoff = result.scalar_one_or_none()
    if handoff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handoff not found")
    if handoff.accepted_by is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Handoff already resolved")

    handoff.accepted_by = user_id
    handoff.accepted_at = datetime.now(timezone.utc)

    # Transition project state
    project = await get_project(db, handoff.project_id)
    if handoff.direction == "creative_to_eng":
        project.state = "eng_active"
    else:
        project.state = "creative_active"

    await db.flush()
    return handoff


async def decline_handoff(db: AsyncSession, handoff_id: str) -> HandoffRecord:
    result = await db.execute(select(HandoffRecord).where(HandoffRecord.id == handoff_id))
    handoff = result.scalar_one_or_none()
    if handoff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handoff not found")
    if handoff.accepted_by is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Handoff already resolved")

    # Revert project state
    project = await get_project(db, handoff.project_id)
    if handoff.direction == "creative_to_eng":
        project.state = "creative_active"
    else:
        project.state = "eng_active"

    # Mark as declined by setting accepted_at without accepted_by (convention)
    handoff.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    return handoff
