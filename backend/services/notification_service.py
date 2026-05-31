"""Notification service — list, mark read."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.notification import Notification


async def list_notifications(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 50
) -> tuple[list[Notification], int]:
    count_result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def mark_read(db: AsyncSession, notification_id: str, user_id: str) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notification.read_at = datetime.now(timezone.utc)
    await db.flush()
    return notification


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    """Mark all unread notifications as read. Returns count updated."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    count = 0
    now = datetime.now(timezone.utc)
    for notification in result.scalars().all():
        notification.read_at = now
        count += 1
    await db.flush()
    return count


async def create_notification(
    db: AsyncSession,
    user_id: str,
    notification_type: str,
    channel: str = "in_app",
    project_id: str | None = None,
    payload: dict | None = None,
) -> Notification:
    """Create and persist a notification. For advanced delivery, prefer send_notification_to_user."""
    notification = Notification(
        user_id=user_id,
        project_id=project_id,
        type=notification_type,
        channel=channel,
        payload=payload or {},
        sent_at=datetime.now(timezone.utc),
        delivered=True,
    )
    db.add(notification)
    await db.flush()
    return notification


async def send_notification_to_user(
    db: AsyncSession,
    user: "User",
    notification_type: str,
    project_id: str | None = None,
    payload: dict | None = None,
) -> list[Notification]:
    """
    Advanced notification delivery: creates in_app + optionally sends email and webhook.
    Respects user.notify_settings for email preferences.
    Returns list of created Notification records.
    """
    from backend.config import get_settings
    settings = get_settings()

    created = []

    # Always create in-app notification
    in_app = await create_notification(
        db, user.id, notification_type, "in_app", project_id, payload
    )
    created.append(in_app)

    # WS push (advanced real-time)
    try:
        from backend.routers.websockets import publish_notification_event
        # Fire and forget (non-blocking)
        import asyncio
        asyncio.create_task(publish_notification_event(user.id, {
            "id": in_app.id,
            "type": notification_type,
            "channel": "in_app",
            "payload": payload or {},
            "created_at": in_app.sent_at.isoformat() if in_app.sent_at else None,
        }))
    except Exception as e:
        logger.warning(f"WS notif publish failed: {e}")

    # Email if configured AND user has email enabled for this type
    email_prefs = (user.notify_settings or {}).get("email", {})
    email_enabled = email_prefs.get(notification_type, True)  # default on for backward compat

    if settings.SMTP_HOST and settings.SMTP_FROM_ADDRESS and user.email and email_enabled:
        try:
            await _send_email_notification(settings, user.email, notification_type, payload or {})
            # Record a separate email notification entry
            email_notif = await create_notification(
                db, user.id, notification_type, "email", project_id, payload
            )
            created.append(email_notif)
        except Exception as e:
            logger.warning(f"Failed to send email notification to {user.email}: {e}")

    # Webhook if configured (could also add per-type prefs later)
    if settings.WEBHOOK_URL:
        try:
            await _send_webhook_notification(settings.WEBHOOK_URL, user.id, notification_type, payload or {})
            webhook_notif = await create_notification(
                db, user.id, notification_type, "webhook", project_id, payload
            )
            created.append(webhook_notif)
        except Exception as e:
            logger.warning(f"Failed to send webhook notification: {e}")

    return created


# Email templates (simple but proper system - can be moved to DB/settings later)
EMAIL_TEMPLATES = {
    "job_completed": {
        "subject": "Job Completed: {job_type} for project {project_id}",
        "body": """Hello,

Your job (type: {job_type}) has completed successfully.

Job ID: {job_id}
Project: {project_id}
Assets created: {asset_count}

Details:
{details}

Best regards,
AIMoveMaker Team
""",
    },
    "render_complete": {
        "subject": "Render Complete for Project {project_id}",
        "body": """Hello,

Your render job has completed.

Job ID: {job_id}
Project: {project_id}
Output Asset: {asset_id}

You can download the final render from the project timeline.

Best regards,
AIMoveMaker Team
""",
    },
    "handoff": {
        "subject": "Project Handoff {handoff_type} - {project_id}",
        "body": """Hello,

A project handoff has occurred.

Project: {project_id}
Handoff ID: {handoff_id}
Type: {handoff_type}

Please review the project in your dashboard.

Best regards,
AIMoveMaker Team
""",
    },
    "approval": {
        "subject": "Account Approved - Welcome to AIMoveMaker",
        "body": """Hello,

Your account has been approved.

You can now log in and start creating projects.

Welcome aboard!

Best regards,
AIMoveMaker Team
""",
    },
    "account_approved": {
        "subject": "Account Approved - Welcome to AIMoveMaker",
        "body": """Hello,

Your account has been approved.

You can now log in and start creating projects.

Welcome aboard!

Best regards,
AIMoveMaker Team
""",
    },
    "project_state_change": {
        "subject": "Project State Updated: {project_id}",
        "body": """Hello,

The state of your project has changed.

Project: {project_id}
New State: {new_state}

Log in to view the latest updates.

Best regards,
AIMoveMaker Team
""",
    },
}

DEFAULT_TEMPLATE = {
    "subject": "[AIMoveMaker] Notification: {notif_type}",
    "body": """Hello,

You have a new notification: {notif_type}

Details:
{details}

Best regards,
AIMoveMaker Team
""",
}

async def _send_email_notification(settings, to_email: str, notif_type: str, payload: dict):
    """SMTP email with proper templates."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    template = EMAIL_TEMPLATES.get(notif_type, DEFAULT_TEMPLATE)

    # Build context
    context = {"notif_type": notif_type, "details": ""}
    context.update(payload)

    # Format details string
    details_lines = []
    for k, v in payload.items():
        details_lines.append(f"  {k}: {v}")
    context["details"] = "\n".join(details_lines) if details_lines else "No additional details."

    subject = template["subject"].format(**context)
    body = template["body"].format(**context)

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def _send_webhook_notification(webhook_url: str, user_id: str, notif_type: str, payload: dict):
    """Outbound webhook POST."""
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            webhook_url,
            json={
                "event": notif_type,
                "user_id": user_id,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
