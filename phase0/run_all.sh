#!/bin/bash
# Phase 0 Test Runner — Linux/WSL
# Runs all Phase 0 GPU tests and saves results.

set -e

MODEL_ROOT="${1:-$HOME/AIModels}"
PRECISION="${2:-fp8}"
MODELS="${3:-all}"

echo "Phase 0 GPU Test Kit — RTX 5090"
echo "============================================================"
echo ""

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  WARNING: Virtual environment not activated"
    echo "   Run: source .venv/bin/activate"
    echo ""
fi

# Step 1: Environment check
echo "Step 1: Environment Check"
echo "============================================================"
python env_check.py --model-root "$MODEL_ROOT"

echo ""
echo "Press Enter to continue with VRAM fit tests (or Ctrl+C to cancel)..."
read -r

# Step 2: VRAM fit tests
echo ""
echo "Step 2: VRAM Fit Tests"
echo "============================================================"
python vram_fit.py --model-root "$MODEL_ROOT" --precision "$PRECISION" --models $MODELS

# Step 3: Converter check (stub)
echo ""
echo "Step 3: Converter Check"
echo "============================================================"
python converter_check.py --model-root "$MODEL_ROOT"

echo ""
echo "============================================================"
echo "Phase 0 Tests Complete!"
echo "============================================================"
echo ""
echo "Results saved to: phase0/results/*.json"
echo ""
echo "Next steps:"
echo "  1. Review results: ls phase0/results/*.json"
echo "  2. Check samples: ls phase0/results/samples/"
echo "  3. Commit results: git add phase0/results/*.json && git commit -m 'phase0: RTX 5090 results'"
echo "  4. Push to GitHub: git push"
echo ""
