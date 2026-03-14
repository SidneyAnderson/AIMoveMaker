#!/usr/bin/env bash
# ============================================================================
# AI Movie Maker — Setup Script
# ============================================================================
# Bootstraps the project on a clean machine. Run once after cloning:
#   chmod +x setup.sh && ./setup.sh
#
# Prerequisites: Python 3.11+, Node.js 18+, Redis 7+ (optional for dev)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

echo ""
echo "==========================================="
echo "   AI Movie Maker — Setup"
echo "==========================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

# Python 3.11+
if ! command -v python3 &> /dev/null; then
    error "python3 not found. Install Python 3.11+ and try again."
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PY_VER"

# Node.js 18+ (for frontend)
if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    info "Node.js version: $NODE_VER"
else
    warn "Node.js not found. Frontend will not be built."
    warn "Install Node.js 18+ for the full experience."
fi

# Redis (optional)
if command -v redis-cli &> /dev/null; then
    info "Redis: found"
else
    warn "Redis not found. Celery worker and real-time features require Redis 7+."
    warn "Install Redis or use Docker: docker run -d -p 6379:6379 redis:7"
fi

echo ""

# ---------------------------------------------------------------------------
# 2. Python virtual environment
# ---------------------------------------------------------------------------
if [ ! -d "venv" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv venv
else
    info "Virtual environment already exists."
fi

info "Activating virtual environment..."
source venv/bin/activate

info "Upgrading pip..."
pip install --upgrade pip -q

info "Installing Python dependencies..."
pip install -r requirements.txt -q

echo ""

# ---------------------------------------------------------------------------
# 3. Directory structure
# ---------------------------------------------------------------------------
info "Creating directory structure..."
mkdir -p data
mkdir -p storage/{assets,outputs,snapshots}
mkdir -p models/{image,video,audio,loras,controlnet}
mkdir -p outputs
mkdir -p snapshots
mkdir -p logs

# Ensure scripts are executable
chmod +x setup.sh start.sh 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. Environment file
# ---------------------------------------------------------------------------
if [ ! -f ".env" ]; then
    info "Creating .env from .env.example..."
    cp .env.example .env
    # Generate a random SECRET_KEY
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/^SECRET_KEY=$/SECRET_KEY=${SECRET}/" .env
    info "Generated random SECRET_KEY in .env"
else
    info ".env already exists, skipping."
fi

echo ""

# ---------------------------------------------------------------------------
# 5. Database migrations
# ---------------------------------------------------------------------------
info "Running database migrations..."
alembic upgrade head

# ---------------------------------------------------------------------------
# 6. Seed database (admin + settings)
# ---------------------------------------------------------------------------
info "Seeding database (admin user + global settings)..."
python3 -m backend.seed

echo ""

# ---------------------------------------------------------------------------
# 7. Frontend dependencies
# ---------------------------------------------------------------------------
if command -v node &> /dev/null && [ -d "frontend" ]; then
    info "Installing frontend dependencies..."
    (cd frontend && npm install --silent 2>&1)
    info "Building frontend..."
    (cd frontend && npm run build 2>&1)
    info "Frontend build complete (dist/ ready)."
else
    warn "Skipping frontend setup (Node.js not found or frontend/ missing)."
fi

echo ""

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "==========================================="
echo -e "   ${GREEN}Setup Complete!${NC}"
echo "==========================================="
echo ""
echo "Next steps:"
echo "  1. Review .env and adjust settings if needed"
echo "  2. Run ./start.sh to start the application"
echo ""
echo -e "${YELLOW}WARNING:${NC} Default admin credentials are:"
echo "  Email:    admin@localhost"
echo "  Password: admin"
echo "  You MUST change this password on first login."
echo ""
