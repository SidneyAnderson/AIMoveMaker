#!/usr/bin/env bash
# ============================================================================
# AI Movie Maker — Setup Script
# ============================================================================
# Bootstraps the project on a clean machine. Run once after cloning:
#   chmod +x setup.sh && ./setup.sh
#
# Prerequisites: Python 3.10+, Node.js 18+, Redis 7+ (optional for dev)
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
# 1. Python virtual environment (must exist before prereq checks)
# ---------------------------------------------------------------------------
if ! command -v python3 &> /dev/null; then
    error "python3 not found. Install Python 3.10+ and try again."
    exit 1
fi

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

# ---------------------------------------------------------------------------
# 2. Verify prerequisites (using the venv Python)
# ---------------------------------------------------------------------------
echo ""
info "Checking prerequisites..."

# Python version
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    error "Python 3.10+ required, found $PY_VER"
    exit 1
fi
info "Python version: $PY_VER ✓"

# Node.js 18+ (for frontend)
if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    info "Node.js version: $NODE_VER ✓"
else
    warn "Node.js not found. Frontend will not be built."
    warn "Install Node.js 18+ for the full experience."
fi

# ffmpeg (required for video/audio processing)
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VER=$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')
    info "ffmpeg: $FFMPEG_VER ✓"
else
    warn "ffmpeg not found. Video/audio processing requires ffmpeg."
    warn "Install with: sudo apt install ffmpeg  (or brew install ffmpeg)"
fi

# Redis (optional)
if command -v redis-cli &> /dev/null; then
    info "Redis: found ✓"
else
    warn "Redis not found. Celery worker and real-time features require Redis 7+."
    warn "Install Redis or use Docker: docker run -d -p 6379:6379 redis:7"
fi

# CUDA GPU
if python3 -c "
import subprocess, sys
try:
    out = subprocess.check_output(['nvidia-smi'], stderr=subprocess.DEVNULL).decode()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
    GPU_NAME=$(python3 -c "
import subprocess, re
out = subprocess.check_output(['nvidia-smi'], stderr=subprocess.DEVNULL).decode()
m = re.search(r'NVIDIA\s+([^\|]+)', out)
print(m.group(1).strip() if m else 'Unknown NVIDIA GPU')
" 2>/dev/null)
    CUDA_VER=$(python3 -c "
import subprocess, re
out = subprocess.check_output(['nvidia-smi'], stderr=subprocess.DEVNULL).decode()

# Detect GPU architecture from name (Blackwell = RTX 50xx series)
is_blackwell = bool(re.search(r'RTX\s*50[0-9]{2}', out))

# Parse CUDA driver version
m = re.search(r'CUDA Version:\s*([\d]+)\.([\d]+)', out)
if m:
    major, minor = int(m.group(1)), int(m.group(2))
    # Blackwell GPUs (sm_120) REQUIRE cu128 minimum for native support
    if is_blackwell:
        print('cu128')
    elif major >= 13:
        # CUDA 13.x drivers → cu128 (best available, backward compat)
        print('cu128')
    elif major == 12 and minor >= 8:
        print('cu128')
    elif major == 12 and minor >= 6:
        print('cu126')
    elif major == 12 and minor >= 4:
        print('cu124')
    elif major >= 12:
        print('cu121')
    elif major == 11 and minor >= 8:
        print('cu118')
    else:
        print('cu121')
else:
    print('cu121')
" 2>/dev/null)
    HAS_CUDA=true
    info "GPU: $GPU_NAME (${CUDA_VER}) ✓"
else
    HAS_CUDA=false
    warn "No CUDA GPU detected. AI pipelines will run on CPU (much slower)."
fi

echo ""

# ---------------------------------------------------------------------------
# 3. Install PyTorch (CUDA or CPU)
# ---------------------------------------------------------------------------
# PyTorch must be installed from the PyTorch index, not PyPI, to get CUDA support.
# We uninstall first to avoid pip saying "already satisfied" with an old/wrong build.
if [ "$HAS_CUDA" = true ]; then
    PYTORCH_INDEX="https://download.pytorch.org/whl/${CUDA_VER}"
    info "Installing PyTorch with ${CUDA_VER} support..."
    # Check if existing torch matches the target CUDA version
    CURRENT_TORCH=$(pip show torch 2>/dev/null | grep "^Version:" | awk '{print $2}' || echo "")
    if [ -n "$CURRENT_TORCH" ]; then
        if echo "$CURRENT_TORCH" | grep -q "${CUDA_VER}"; then
            info "PyTorch $CURRENT_TORCH already installed with ${CUDA_VER}."
        else
            info "Replacing PyTorch $CURRENT_TORCH with ${CUDA_VER} build..."
            pip uninstall torch torchvision torchaudio -y -q 2>/dev/null || true
        fi
    fi
    pip install torch torchvision torchaudio --index-url "$PYTORCH_INDEX" -q
    # Install xformers for memory-efficient attention (matches PyTorch CUDA build)
    info "Installing xformers..."
    pip install xformers --index-url "$PYTORCH_INDEX" -q 2>/dev/null || \
        warn "xformers installation failed (optional — PyTorch SDPA will be used instead)."
else
    info "Installing PyTorch (CPU only)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu -q
fi

# ---------------------------------------------------------------------------
# 4. Install remaining Python dependencies
# ---------------------------------------------------------------------------
info "Installing Python dependencies..."
pip install -r requirements.txt -q

# ---- Coqui TTS (installed separately due to strict numpy pin on Python 3.10) ----
info "Installing Coqui TTS..."
pip install TTS==0.22.0 --no-deps -q 2>/dev/null
# Install TTS runtime dependencies (skipping numpy/pandas which conflict on Python 3.10)
pip install trainer coqpit gruut bangla bnnumerizer bnunicodenormalizer \
    unidecode pypinyin encodec g2pkk jieba pysbd anyascii inflect \
    matplotlib hangul-romanize cython aiohttp umap-learn flask -q 2>/dev/null || true

echo ""

# ---------------------------------------------------------------------------
# 5. Directory structure
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
# 6. Environment file
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
# 7. Database migrations
# ---------------------------------------------------------------------------
info "Running database migrations..."
alembic upgrade head

# ---------------------------------------------------------------------------
# 8. Seed database (admin + settings)
# ---------------------------------------------------------------------------
info "Seeding database (admin user + global settings)..."
python3 -m backend.seed

echo ""

# ---------------------------------------------------------------------------
# 9. Frontend dependencies
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
