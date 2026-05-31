"""Prompt template and history service."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.prompt_history import PromptHistory
from backend.models.prompt_template import PromptTemplate


async def list_templates(
    db: AsyncSession, user_id: str, project_id: str | None = None, skip: int = 0, limit: int = 20
) -> tuple[list[PromptTemplate], int]:
    """List templates visible to user (global + their project ones)."""
    q = select(PromptTemplate).where(
        (PromptTemplate.scope == "global") |
        (PromptTemplate.scope_project_id == project_id) |
        (PromptTemplate.owner_id == user_id)
    )
    if project_id:
        q = q.where(
            (PromptTemplate.scope == "global") |
            (PromptTemplate.scope_project_id == project_id)
        )
    cq = select(func.count()).select_from(PromptTemplate).where(
        (PromptTemplate.scope == "global") |
        (PromptTemplate.scope_project_id == project_id) |
        (PromptTemplate.owner_id == user_id)
    )

    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(q.order_by(PromptTemplate.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def create_template(db: AsyncSession, user_id: str, data: dict) -> PromptTemplate:
    template = PromptTemplate(owner_id=user_id, **data)
    db.add(template)
    await db.flush()
    return template


async def apply_template(db: AsyncSession, template_id: str, user_id: str) -> dict:
    """Return the template data to apply to a keyframe/form."""
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    # Basic visibility check
    if template.scope == "project" and template.scope_project_id:
        # In real, check membership, but for now allow
        pass
    return {
        "positive_prompt": template.positive_prompt,
        "negative_prompt": template.negative_prompt,
        "model_id": template.model_id,
        "lora_stack": template.lora_stack,
        "params": template.params,
    }


async def list_history(
    db: AsyncSession, user_id: str, project_id: str | None = None, skip: int = 0, limit: int = 20
) -> tuple[list[PromptHistory], int]:
    q = select(PromptHistory).where(PromptHistory.user_id == user_id)
    if project_id:
        q = q.where(PromptHistory.project_id == project_id)
    cq = select(func.count()).select_from(PromptHistory).where(PromptHistory.user_id == user_id)
    if project_id:
        cq = cq.where(PromptHistory.project_id == project_id)

    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(q.order_by(PromptHistory.used_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def create_history(db: AsyncSession, user_id: str, data: dict) -> PromptHistory:
    history = PromptHistory(user_id=user_id, **data)
    db.add(history)
    await db.flush()
    return history
