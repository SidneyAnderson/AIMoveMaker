#!/usr/bin/env bash
# ============================================================================
# AI Movie Maker — Start Script
# ============================================================================
# Launches all services: Redis check, Celery worker, FastAPI, Vite dev server.
# Usage:
#   ./start.sh          # Start backend + frontend (dev mode)
#   ./start.sh --api    # Start backend only (API server + Celery)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

API_ONLY=false
if [[ "${1:-}" == "--api" ]]; then
    API_ONLY=true
fi

echo ""
echo "==========================================="
echo "   AI Movie Maker"
echo "==========================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Virtual environment
# ---------------------------------------------------------------------------
if [ ! -d "venv" ]; then
    error "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi
source venv/bin/activate
info "Virtual environment: activated"

# ---------------------------------------------------------------------------
# 2. Redis
# ---------------------------------------------------------------------------
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null 2>&1; then
        info "Redis: running"
    else
        info "Starting Redis..."
        redis-server --daemonize yes 2>/dev/null || warn "Could not start Redis as daemon"
        sleep 1
        if redis-cli ping &> /dev/null 2>&1; then
            info "Redis: started"
        else
            warn "Redis failed to start. Celery and real-time features unavailable."
        fi
    fi
else
    warn "Redis not installed. Celery worker and WebSocket streaming disabled."
fi

# ---------------------------------------------------------------------------
# 3. Celery worker (background)
# ---------------------------------------------------------------------------
if command -v celery &> /dev/null && redis-cli ping &> /dev/null 2>&1; then
    info "Starting Celery worker (background)..."
    celery -A backend.celery_app worker \
        --loglevel=info \
        --logfile=logs/celery.log \
        --pidfile=logs/celery.pid \
        --detach 2>/dev/null && info "Celery worker: started" \
        || warn "Celery worker failed to start (non-critical for dev)"
else
    warn "Skipping Celery worker (redis or celery not available)"
fi

# ---------------------------------------------------------------------------
# 4. Frontend dev server (background, unless --api)
# ---------------------------------------------------------------------------
FRONTEND_PID=""
if [[ "$API_ONLY" == "false" ]] && command -v node &> /dev/null && [ -d "frontend" ]; then
    info "Starting Vite dev server on http://localhost:5173 (background)..."
    (cd frontend && npm run dev > ../logs/vite.log 2>&1) &
    FRONTEND_PID=$!
    info "Vite dev server: PID $FRONTEND_PID"
fi

# ---------------------------------------------------------------------------
# 5. FastAPI server (foreground)
# ---------------------------------------------------------------------------
echo ""
info "Starting FastAPI server on http://0.0.0.0:8000"
info "API docs:  http://localhost:8000/docs"
if [[ -n "$FRONTEND_PID" ]]; then
    info "Frontend:  http://localhost:5173"
fi
echo ""

# Trap to clean up background processes on exit
cleanup() {
    if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        info "Stopping Vite dev server..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    # Stop Celery if we have a pidfile
    if [ -f "logs/celery.pid" ]; then
        CELERY_PID=$(cat logs/celery.pid 2>/dev/null)
        if [[ -n "$CELERY_PID" ]] && kill -0 "$CELERY_PID" 2>/dev/null; then
            info "Stopping Celery worker..."
            kill "$CELERY_PID" 2>/dev/null || true
        fi
    fi
}
trap cleanup EXIT

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
