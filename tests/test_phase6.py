"""Phase 6 (Integration & Hardening) verification tests.

Checks all PRD Phase 6 deliverables:
1. setup.sh and start.sh finalized
2. .env.example with all environment variables documented
3. Log rotation configured
4. Section 10.1 open items resolved or deferred with code comments
5. README written covering installation, first-run, and basic usage
"""
import os
import sys

PROJECT_DIR = "/home/sid/AIMoveMaker"

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")


def read(rel_path: str) -> str:
    with open(os.path.join(PROJECT_DIR, rel_path)) as f:
        return f.read()


def file_exists(rel_path: str) -> bool:
    return os.path.exists(os.path.join(PROJECT_DIR, rel_path))


# ── Test 1: setup.sh ────────────────────────────────────────────────
print("\nTest 1: setup.sh")
check("setup.sh exists", file_exists("setup.sh"))
setup = read("setup.sh")
check("shebang present", setup.startswith("#!/"), "Missing shebang")
check("creates venv", "venv" in setup, "No venv creation")
check("pip install", "pip install" in setup, "No pip install")
check("requirements.txt", "requirements.txt" in setup, "No requirements.txt reference")
check("alembic upgrade", "alembic upgrade" in setup, "No Alembic migration")
check("seed database", "seed" in setup, "No database seeding")
check("SECRET_KEY generation", "SECRET" in setup or "secret" in setup, "No SECRET_KEY generation")
check(".env creation", ".env" in setup, "No .env file handling")
check("mkdir directories", "mkdir" in setup, "No directory creation")
check("frontend npm install", "npm install" in setup, "No frontend dependency install")
check("frontend build", "npm run build" in setup, "No frontend build")
check("set -e for error handling", "set -e" in setup, "No error handling")

# ── Test 2: start.sh ────────────────────────────────────────────────
print("\nTest 2: start.sh")
check("start.sh exists", file_exists("start.sh"))
start = read("start.sh")
check("shebang present", start.startswith("#!/"), "Missing shebang")
check("venv activation", "source" in start and "venv" in start, "No venv activation")
check("Redis check", "redis" in start.lower(), "No Redis handling")
check("Celery worker", "celery" in start.lower(), "No Celery worker")
check("uvicorn start", "uvicorn" in start, "No uvicorn")
check("backend.main:app", "backend.main:app" in start, "Wrong app reference")
check("frontend dev server", "npm run dev" in start or "vite" in start.lower(), "No frontend dev server")
check("cleanup trap", "trap" in start, "No cleanup trap for background processes")
check("--api flag support", "--api" in start, "No --api flag for API-only mode")
check("celery_app reference", "celery_app" in start, "References old tasks.worker instead of celery_app")

# ── Test 3: .env.example ────────────────────────────────────────────
print("\nTest 3: .env.example")
check(".env.example exists", file_exists(".env.example"))
env = read(".env.example")
required_vars = [
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "ENVIRONMENT",
    "LOG_LEVEL",
    "STORAGE_BASE_PATH",
    "VITE_API_URL",
    "VITE_WS_URL",
]
for var in required_vars:
    check(f"env var: {var}", var in env, f"Missing {var}")
check("openssl instruction", "openssl rand" in env, "No openssl SECRET_KEY instruction")
check("infrastructure-only note", "infrastructure" in env.lower() or "Setting table" in env,
      "Missing note about runtime config in Setting table")

# ── Test 4: Log rotation configured ─────────────────────────────────
print("\nTest 4: Log rotation")
check("logging_config.py exists", file_exists("backend/logging_config.py"))
if file_exists("backend/logging_config.py"):
    logcfg = read("backend/logging_config.py")
    check("loguru import", "loguru" in logcfg, "No loguru import")
    check("file rotation (50 MB)", "50 MB" in logcfg or "rotation" in logcfg,
          "No file rotation configured")
    check("log retention", "retention" in logcfg, "No retention policy")
    check("compression", "compression" in logcfg or "gz" in logcfg,
          "No log compression")
    check("JSON sink", "serialize" in logcfg or "json" in logcfg.lower(),
          "No JSON structured logging")
    check("console sink", "stderr" in logcfg or "stdout" in logcfg,
          "No console sink")
    check("app.log output", "app.log" in logcfg, "No app.log file")

# Log rotation integrated into main.py
main = read("backend/main.py")
check("logging_config imported in main.py",
      "logging_config" in main or "configure_logging" in main,
      "logging_config not integrated into app startup")

# logs directory in setup.sh
check("logs/ directory created by setup.sh", "logs" in setup,
      "setup.sh doesn't create logs/ directory")

# ── Test 5: Section 10.1 open items ─────────────────────────────────
print("\nTest 5: PRD Section 10.1 open items")

# Item 1: Lip sync model (wav2lip vs SadTalker)
audio = read("backend/pipelines/audio.py")
check("Item 1: Lip sync model comment",
      "Section 10.1" in audio and ("wav2lip" in audio) and ("SadTalker" in audio or "DEFERRED" in audio),
      "Missing Section 10.1 lip sync model resolution")

# Item 2: Real-ESRGAN upscaling
image = read("backend/pipelines/image.py")
check("Item 2: Real-ESRGAN comment",
      "Section 10.1" in image and ("ESRGAN" in image or "upscal" in image.lower()),
      "Missing Section 10.1 Real-ESRGAN resolution")

# Item 3: Audio export formats
check("Item 3: Audio export formats comment",
      "Section 10.1" in audio and ("WAV" in audio or "FLAC" in audio or "audio export" in audio.lower()),
      "Missing Section 10.1 audio export formats resolution")

# Item 4: xformers sm_120
hw = read("backend/hardware_profile.py")
check("Item 4: xformers sm_120 comment",
      "Section 10.1" in hw and ("xformers" in hw) and ("sm_120" in hw or "SDPA" in hw),
      "Missing Section 10.1 xformers resolution")

# ── Test 6: README.md ───────────────────────────────────────────────
print("\nTest 6: README.md")
check("README.md exists", file_exists("README.md"))
readme = read("README.md")
check("README is substantive (>500 chars)", len(readme) > 500,
      f"README too short ({len(readme)} chars)")

# Installation section
check("installation instructions",
      "install" in readme.lower() or "setup" in readme.lower(),
      "No installation instructions")
check("setup.sh reference", "setup.sh" in readme, "No setup.sh reference")
check("start.sh reference", "start.sh" in readme, "No start.sh reference")

# First-run section
check("first-run / default credentials",
      "admin@localhost" in readme or "admin" in readme.lower(),
      "No default credentials")
check("port 8000 or URL", "8000" in readme or "localhost" in readme,
      "No server URL/port")

# Basic usage
check("workflow steps",
      ("login" in readme.lower() and "project" in readme.lower()),
      "No workflow/usage steps")
check("API docs reference", "docs" in readme.lower() or "swagger" in readme.lower(),
      "No API docs reference")

# Project structure
check("project structure",
      "structure" in readme.lower() or "backend/" in readme,
      "No project structure section")

# Environment variables table
check("env vars documented in README",
      "DATABASE_URL" in readme and "SECRET_KEY" in readme,
      "Environment variables not in README")

# ── Test 7: Directory structure ──────────────────────────────────────
print("\nTest 7: Required directories and files")
required_paths = [
    "backend/__init__.py",
    "backend/main.py",
    "backend/config.py",
    "backend/models/__init__.py",
    "backend/schemas/__init__.py",
    "backend/celery_app.py",
    "backend/seed.py",
    "backend/hardware_profile.py",
    "backend/logging_config.py",
    "backend/dependencies.py",
    "backend/routers/__init__.py",
    "backend/services/__init__.py",
    "backend/pipelines/__init__.py",
    "backend/tasks/__init__.py",
    "backend/migrations/env.py",
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "requirements.txt",
    ".env.example",
    "setup.sh",
    "start.sh",
    "README.md",
]
for p in required_paths:
    check(f"exists: {p}", file_exists(p), f"Missing {p}")

# ── Test 8: Backend app loads ────────────────────────────────────────
print("\nTest 8: Backend app loads")
try:
    sys.path.insert(0, PROJECT_DIR)
    os.chdir(PROJECT_DIR)
    from backend.main import app
    routes = [r.path for r in app.routes]
    check("app has routes", len(routes) > 40, f"Only {len(routes)} routes")
    check("health/docs route", "/docs" in routes or "/openapi.json" in routes,
          "Missing /docs or /openapi.json")
except Exception as e:
    check("app loads", False, str(e))

# ── Test 9: Logging config importable ────────────────────────────────
print("\nTest 9: Logging config importable")
try:
    from backend.logging_config import configure_logging
    check("configure_logging importable", True)
except Exception as e:
    check("configure_logging importable", False, str(e))

# ── Summary ──────────────────────────────────────────────────────────
total = passed + failed
print(f"\n{'='*60}")
print(f"Phase 6 Verification: {passed}/{total} passed, {failed} failed")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
