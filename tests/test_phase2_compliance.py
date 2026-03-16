"""
Phase 2 PRD Compliance Tests
=============================
Tests all 5 Phase 2 fixes against the running API server:
  1. storage_path excluded from AssetResponse, ModelRegistryResponse, LoRARegistryResponse
  2. Integration endpoints require auth (PRD 8.4)
  3. All list endpoints use {items, total, page, page_size, pages} envelope (PRD 13.11)
  4. TokenResponse UserInfo includes approval_state (PRD 13.1)
  5. Asset upload handler uses correct field names (type, subtype, storage_path)
"""
import io
import sys
import requests

BASE = "http://localhost:8000/api"
PASS = 0
FAIL = 0
ERRORS = []


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        ERRORS.append(f"{name}: {detail}")


def get_token(email="admin@localhost", password="admin"):
    """Login and return bearer token."""
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"], r.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Login + change forced password
# ===========================================================================
print("\n🔐 Logging in as admin...")
token, login_data = get_token()
headers = auth_headers(token)

# Admin has force_password_change=true — change password first
if login_data.get("force_password_change"):
    print("  Changing forced password...")
    r = requests.post(f"{BASE}/auth/change-password", headers=headers, json={
        "current_password": "admin",
        "new_password": "Admin123!@#Secure",
    })
    assert r.status_code == 200, f"Password change failed: {r.status_code} {r.text}"
    # Re-login with new password
    token, login_data = get_token("admin@localhost", "Admin123!@#Secure")
    headers = auth_headers(token)
print(f"  Token obtained ✓\n")


# ===========================================================================
# FIX 4: TokenResponse UserInfo includes approval_state
# ===========================================================================
print("═══ FIX 4: TokenResponse UserInfo includes approval_state ═══")
user_info = login_data.get("user", {})
test("user object present in token response", user_info is not None and len(user_info) > 0)
test("approval_state in user info", "approval_state" in user_info,
     f"keys: {list(user_info.keys())}")
test("approval_state value is 'approved' for admin", user_info.get("approval_state") == "approved",
     f"got: {user_info.get('approval_state')}")
test("global_role in user info", "global_role" in user_info)
test("force_password_change in user info", "force_password_change" in user_info)
print()


# ===========================================================================
# FIX 2: Integration endpoints require auth (PRD 8.4)
# ===========================================================================
print("═══ FIX 2: Integration endpoints require JWT auth ═══")

# Test WITHOUT auth — should get 401
r = requests.get(f"{BASE}/integrations/civitai/search")
test("civitai/search without auth → 401", r.status_code == 401, f"got {r.status_code}")

r = requests.get(f"{BASE}/integrations/huggingface/search")
test("huggingface/search without auth → 401", r.status_code == 401, f"got {r.status_code}")

r = requests.get(f"{BASE}/integrations/vastai/offers")
test("vastai/offers without auth → 401", r.status_code == 401, f"got {r.status_code}")

# Test WITH auth — should succeed (200)
r = requests.get(f"{BASE}/integrations/civitai/search", headers=headers)
test("civitai/search with auth → 200", r.status_code == 200, f"got {r.status_code}")

r = requests.get(f"{BASE}/integrations/huggingface/search", headers=headers)
test("huggingface/search with auth → 200", r.status_code == 200, f"got {r.status_code}")

r = requests.get(f"{BASE}/integrations/vastai/offers", headers=headers)
test("vastai/offers with auth → 200", r.status_code == 200, f"got {r.status_code}")
print()


# ===========================================================================
# FIX 3: All list endpoints use {items, total, page, page_size, pages}
# ===========================================================================
print("═══ FIX 3: Paginated list envelope {items, total, page, page_size, pages} ═══")

# Create a project for nested list endpoints
r = requests.post(f"{BASE}/projects/", headers=headers, json={
    "title": "Test Project",
    "description": "For compliance testing",
    "fps": 24,
})
assert r.status_code == 201, f"Project creation failed: {r.status_code} {r.text}"
project_id = r.json()["id"]
print(f"  Created project: {project_id}")

ENVELOPE_KEYS = {"items", "total", "page", "page_size", "pages"}
OLD_KEYS = {"users", "projects", "assets", "storyboards", "keyframes",
            "settings", "notifications", "invites", "models", "loras",
            "jobs", "batches", "timelines", "tracks", "video_clips",
            "audio_clips", "members", "handoffs", "snapshots"}


def check_list_envelope(endpoint_path, label):
    """Check that a list endpoint returns the correct paginated envelope."""
    r = requests.get(f"{BASE}{endpoint_path}", headers=headers)
    if r.status_code != 200:
        test(f"{label} → 200", False, f"got {r.status_code}: {r.text[:100]}")
        return
    data = r.json()
    has_all_keys = ENVELOPE_KEYS.issubset(set(data.keys()))
    test(f"{label} has {{items, total, page, page_size, pages}}", has_all_keys,
         f"keys: {list(data.keys())}")
    test(f"{label} 'items' is a list", isinstance(data.get("items"), list),
         f"type: {type(data.get('items'))}")

    bad_keys = OLD_KEYS.intersection(set(data.keys()))
    test(f"{label} no old domain keys", len(bad_keys) == 0,
         f"found old keys: {bad_keys}")


# Users list
check_list_envelope("/users/", "GET /users/")

# Projects list
check_list_envelope("/projects/", "GET /projects/")

# Project members list (note: no trailing slash in some cases, try both)
r = requests.get(f"{BASE}/projects/{project_id}/members", headers=headers)
if r.status_code == 200:
    check_list_envelope(f"/projects/{project_id}/members", "GET /projects/:id/members")
else:
    check_list_envelope(f"/projects/{project_id}/members/", "GET /projects/:id/members/")

# Project handoffs
r = requests.get(f"{BASE}/projects/{project_id}/handoffs", headers=headers)
if r.status_code == 200:
    check_list_envelope(f"/projects/{project_id}/handoffs", "GET /projects/:id/handoffs")

# Settings list (admin)
check_list_envelope("/settings/", "GET /settings/")

# Keyframes list (under project directly)
check_list_envelope(f"/projects/{project_id}/keyframes/", "GET /keyframes/")

# Assets list
check_list_envelope(f"/projects/{project_id}/assets/", "GET /assets/")

# Notifications
check_list_envelope("/notifications/", "GET /notifications/")

# Invites
check_list_envelope("/invites/", "GET /invites/")

# Jobs
check_list_envelope("/jobs/", "GET /jobs/")

# Model registry
check_list_envelope("/models/", "GET /models/")

# LoRA registry
check_list_envelope("/loras/", "GET /loras/")

# Snapshots
check_list_envelope(f"/projects/{project_id}/snapshots/", "GET /snapshots/")

# Tracks (under project)
check_list_envelope(f"/projects/{project_id}/tracks/", "GET /tracks/")

# Video clips (under project)
check_list_envelope(f"/projects/{project_id}/videoclips/", "GET /videoclips/")

# Audio clips (under project)
check_list_envelope(f"/projects/{project_id}/audioclips/", "GET /audioclips/")

# Batches
check_list_envelope("/batches/", "GET /batches/")
print()


# ===========================================================================
# FIX 1: storage_path excluded from response schemas (PRD 13.11)
# ===========================================================================
print("═══ FIX 1: storage_path excluded from API responses ═══")

# Upload an asset to test
files = {"file": ("test.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "image/png")}
r = requests.post(f"{BASE}/projects/{project_id}/assets/", headers=headers, files=files)
if r.status_code == 201:
    asset_data = r.json()
    test("asset upload returns 201", True)
    test("storage_path NOT in asset response", "storage_path" not in asset_data,
         f"keys: {list(asset_data.keys())}")
    test("asset has 'type' field", "type" in asset_data)
    test("asset has 'subtype' field", "subtype" in asset_data)
    test("asset has 'mime_type' field", "mime_type" in asset_data)
    test("asset has 'file_size_bytes' field", "file_size_bytes" in asset_data)
    test("asset type is 'image'", asset_data.get("type") == "image",
         f"got: {asset_data.get('type')}")
    test("asset subtype is 'still'", asset_data.get("subtype") == "still",
         f"got: {asset_data.get('subtype')}")
    asset_id = asset_data["id"]

    # GET single asset
    r = requests.get(f"{BASE}/projects/{project_id}/assets/{asset_id}", headers=headers)
    if r.status_code == 200:
        get_data = r.json()
        test("GET asset: storage_path NOT in response", "storage_path" not in get_data,
             f"keys: {list(get_data.keys())}")
    else:
        test("GET asset returns 200", False, f"got {r.status_code}")

    # Asset list items
    r = requests.get(f"{BASE}/projects/{project_id}/assets/", headers=headers)
    if r.status_code == 200:
        list_data = r.json()
        if list_data.get("items") and len(list_data["items"]) > 0:
            test("asset list items: no storage_path",
                 "storage_path" not in list_data["items"][0],
                 f"keys: {list(list_data['items'][0].keys())}")
else:
    test("asset upload returns 201", False, f"got {r.status_code}: {r.text[:200]}")

# Check OpenAPI schema for response models
r = requests.get("http://localhost:8000/openapi.json")
if r.status_code == 200:
    openapi = r.json()
    schemas = openapi.get("components", {}).get("schemas", {})

    model_schema = schemas.get("ModelRegistryResponse", {}).get("properties", {})
    test("ModelRegistryResponse schema: no storage_path", "storage_path" not in model_schema,
         f"properties: {list(model_schema.keys())}")

    lora_schema = schemas.get("LoRARegistryResponse", {}).get("properties", {})
    test("LoRARegistryResponse schema: no storage_path", "storage_path" not in lora_schema,
         f"properties: {list(lora_schema.keys())}")

    asset_schema = schemas.get("AssetResponse", {}).get("properties", {})
    test("AssetResponse schema: no storage_path", "storage_path" not in asset_schema,
         f"properties: {list(asset_schema.keys())}")

    user_info_schema = schemas.get("UserInfo", {}).get("properties", {})
    test("UserInfo schema: has approval_state", "approval_state" in user_info_schema,
         f"properties: {list(user_info_schema.keys())}")
else:
    test("OpenAPI fetch", False, f"got {r.status_code}")
print()


# ===========================================================================
# FIX 5: Asset upload uses correct field names
# ===========================================================================
print("═══ FIX 5: Asset upload handler field names ═══")

# Upload audio asset
files = {"file": ("test.mp3", io.BytesIO(b"\xff\xfb\x90\x00" + b"\x00" * 100), "audio/mpeg")}
r = requests.post(f"{BASE}/projects/{project_id}/assets/", headers=headers, files=files)
if r.status_code == 201:
    audio_data = r.json()
    test("audio upload → 201", True)
    test("audio type is 'audio'", audio_data.get("type") == "audio",
         f"got: {audio_data.get('type')}")
    test("audio subtype is 'music'", audio_data.get("subtype") == "music",
         f"got: {audio_data.get('subtype')}")
    test("audio mime_type is 'audio/mpeg'", audio_data.get("mime_type") == "audio/mpeg",
         f"got: {audio_data.get('mime_type')}")
else:
    test("audio upload → 201", False, f"got {r.status_code}: {r.text[:200]}")

# Upload video asset
files = {"file": ("test.mp4", io.BytesIO(b"\x00\x00\x00\x1cftyp" + b"\x00" * 100), "video/mp4")}
r = requests.post(f"{BASE}/projects/{project_id}/assets/", headers=headers, files=files)
if r.status_code == 201:
    video_data = r.json()
    test("video upload → 201", True)
    test("video type is 'video'", video_data.get("type") == "video",
         f"got: {video_data.get('type')}")
    test("video subtype is 'clip'", video_data.get("subtype") == "clip",
         f"got: {video_data.get('subtype')}")
else:
    test("video upload → 201", False, f"got {r.status_code}: {r.text[:200]}")

# Upload other/unknown asset
files = {"file": ("test.bin", io.BytesIO(b"\x00" * 50), "application/octet-stream")}
r = requests.post(f"{BASE}/projects/{project_id}/assets/", headers=headers, files=files)
if r.status_code == 201:
    other_data = r.json()
    test("other upload → 201", True)
    test("other type is 'other'", other_data.get("type") == "other",
         f"got: {other_data.get('type')}")
    test("other subtype is 'export'", other_data.get("subtype") == "export",
         f"got: {other_data.get('subtype')}")
else:
    test("other upload → 201", False, f"got {r.status_code}: {r.text[:200]}")
print()


# ===========================================================================
# BONUS: Public endpoints remain accessible without auth
# ===========================================================================
print("═══ BONUS: Public endpoints accessible without JWT ═══")
# Login should work without bearer (it's the auth endpoint itself)
r = requests.post(f"{BASE}/auth/login", json={
    "email": "admin@localhost", "password": "Admin123!@#Secure"
})
test("POST /auth/login accessible without bearer", r.status_code == 200,
     f"got {r.status_code}")

# Users/me should work WITH auth
r = requests.get(f"{BASE}/users/me", headers=headers)
test("GET /users/me with auth → 200", r.status_code == 200,
     f"got {r.status_code}")
print()


# ===========================================================================
# Summary
# ===========================================================================
TOTAL = PASS + FAIL
print("═══════════════════════════════════════════════")
print(f"  Results: {PASS}/{TOTAL} passed, {FAIL} failed")
print("═══════════════════════════════════════════════")

if ERRORS:
    print("\n❌ Failures:")
    for e in ERRORS:
        print(f"   • {e}")

sys.exit(0 if FAIL == 0 else 1)
