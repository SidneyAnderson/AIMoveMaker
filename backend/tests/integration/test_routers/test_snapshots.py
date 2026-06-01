import pytest

from backend.dependencies import get_current_active_user
from backend.main import app
from backend.models.user import User
from backend.services import snapshot_service
from backend.services.project_service import create_project


@pytest.mark.asyncio
async def test_snapshot_api_supports_tiers_without_exposing_storage_path(
    client, db_session, tmp_path, monkeypatch
):
    user = User(
        id="11111111-1111-4111-8111-111111111111",
        email="admin@example.test",
        full_name="Admin",
        password_hash=None,
        global_role="admin",
        is_active=True,
        approval_state="approved",
        force_password_change=False,
    )
    db_session.add(user)
    await db_session.flush()

    project = await create_project(
        db_session,
        user.id,
        {
            "title": "Snapshot Test",
            "description": None,
            "fps": 24,
            "resolution_w": 1280,
            "resolution_h": 720,
        },
    )
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_active_user] = override_current_user
    monkeypatch.setattr(snapshot_service.settings, "STORAGE_BASE_PATH", str(tmp_path))

    create_response = await client.post(
        f"/api/projects/{project.id}/snapshots/",
        json={"type": "manual", "tier": "major", "label": "Milestone"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["tier"] == "major"
    assert created["label"] == "Milestone"
    assert "storage_path" not in created

    list_response = await client.get(
        f"/api/projects/{project.id}/snapshots/",
        params={"tier": "major"},
    )

    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["items"][0]["tier"] == "major"
    assert "storage_path" not in listed["items"][0]


@pytest.mark.asyncio
async def test_snapshot_openapi_schema_hides_storage_path(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    snapshot_properties = (
        response.json()
        .get("components", {})
        .get("schemas", {})
        .get("SnapshotResponse", {})
        .get("properties", {})
    )

    assert "storage_path" not in snapshot_properties
