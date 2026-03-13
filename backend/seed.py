"""Bootstrap seed: creates default admin user and required global settings."""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session_factory
from backend.models.user import User
from backend.models.setting import Setting

# Required global settings from PRD Section 7.20.1
REQUIRED_SETTINGS = [
    {"key": "vastai_api_key", "value": "", "value_type": "string", "description": "Vast.ai API key", "is_secret": True},
    {"key": "civitai_api_key", "value": "", "value_type": "string", "description": "Civitai API key", "is_secret": True},
    {"key": "hf_token", "value": "", "value_type": "string", "description": "HuggingFace token", "is_secret": True},
    {"key": "default_gpu_target", "value": "local", "value_type": "string", "description": "Default GPU target for new jobs", "is_secret": False},
    {"key": "gpu_optimization_override", "value": "", "value_type": "string", "description": "Overrides Hardware Profile Service. Empty = auto.", "is_secret": False},
    {"key": "default_auto_save_interval_s", "value": "300", "value_type": "int", "description": "System-wide auto-save default", "is_secret": False},
    {"key": "smtp_host", "value": "", "value_type": "string", "description": "SMTP host", "is_secret": False},
    {"key": "smtp_port", "value": "587", "value_type": "int", "description": "SMTP port", "is_secret": False},
    {"key": "smtp_user", "value": "", "value_type": "string", "description": "SMTP user", "is_secret": True},
    {"key": "smtp_password", "value": "", "value_type": "string", "description": "SMTP password", "is_secret": True},
    {"key": "smtp_from_address", "value": "", "value_type": "string", "description": "SMTP from address", "is_secret": False},
    {"key": "default_video_duration_s", "value": "4", "value_type": "int", "description": "Default VideoClip duration from storyboard import", "is_secret": False},
    {"key": "max_batch_size", "value": "50", "value_type": "int", "description": "Max jobs per batch", "is_secret": False},
    {"key": "vram_safety_margin_pct", "value": "10", "value_type": "int", "description": "VRAM headroom % before cloud routing warning", "is_secret": False},
    {"key": "elevenlabs_api_key", "value": "", "value_type": "string", "description": "Audio API fallback", "is_secret": True},
    {"key": "suno_api_key", "value": "", "value_type": "string", "description": "Music API fallback", "is_secret": True},
    {"key": "google_oauth_client_id", "value": "", "value_type": "string", "description": "Google OAuth app client ID", "is_secret": False},
    {"key": "google_oauth_client_secret", "value": "", "value_type": "string", "description": "Google OAuth app client secret", "is_secret": True},
    {"key": "discord_oauth_client_id", "value": "", "value_type": "string", "description": "Discord OAuth app client ID", "is_secret": False},
    {"key": "discord_oauth_client_secret", "value": "", "value_type": "string", "description": "Discord OAuth app client secret", "is_secret": True},
    {"key": "allow_self_registration", "value": "false", "value_type": "bool", "description": "If true, login page shows Register button", "is_secret": False},
]


async def seed_admin(session: AsyncSession, admin_id: str) -> bool:
    """Create bootstrap admin account. Returns True if created, False if exists."""
    result = await session.execute(
        select(User).where(User.email == "admin@localhost")
    )
    if result.scalar_one_or_none():
        return False

    from passlib.hash import bcrypt

    admin = User(
        id=admin_id,
        email="admin@localhost",
        full_name="Administrator",
        password_hash=bcrypt.using(rounds=12).hash("admin"),
        global_role="admin",
        is_active=True,
        approval_state="approved",
        force_password_change=True,
    )
    session.add(admin)
    return True


async def seed_settings(session: AsyncSession, admin_id: str) -> int:
    """Seed required global settings. Returns count of newly created settings."""
    count = 0
    for s in REQUIRED_SETTINGS:
        result = await session.execute(
            select(Setting).where(Setting.key == s["key"], Setting.scope == "global")
        )
        if result.scalar_one_or_none():
            continue
        setting = Setting(
            id=str(uuid.uuid4()),
            key=s["key"],
            value=s["value"],
            value_type=s["value_type"],
            scope="global",
            description=s["description"],
            is_secret=s["is_secret"],
            updated_by=admin_id,
        )
        session.add(setting)
        count += 1
    return count


async def run_seed():
    admin_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        created = await seed_admin(session, admin_id)
        if created:
            print("Bootstrap admin account created: admin@localhost / admin")
            print("WARNING: Change the default password immediately on first login.")
        else:
            # Get existing admin id for settings seed
            result = await session.execute(
                select(User).where(User.email == "admin@localhost")
            )
            admin = result.scalar_one()
            admin_id = admin.id
            print("Admin account already exists, skipping.")

        settings_count = await seed_settings(session, admin_id)
        if settings_count:
            print(f"Seeded {settings_count} global settings.")
        else:
            print("All global settings already exist, skipping.")

        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(run_seed())
