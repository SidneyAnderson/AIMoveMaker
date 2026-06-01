"""Shared test fixtures for the AI Movie Maker test suite."""
import asyncio
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import get_db
from backend.main import app
from backend.models import *  # noqa: F401, F403 — register all models


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_engine(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / f"test_{uuid.uuid4().hex}.db"
    test_database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    repo_root = Path(__file__).resolve().parents[2]

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": test_database_url,
            "SECRET_KEY": "test-secret",
            "ENVIRONMENT": "test",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr

    engine = create_async_engine(test_database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(test_engine):
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
