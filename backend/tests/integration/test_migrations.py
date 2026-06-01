import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_head_creates_snapshot_tier_column(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    db_path = tmp_path / "migration.db"

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
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

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(snapshots)")}

    assert "tier" in columns
