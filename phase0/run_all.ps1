# Phase 0 Test Runner — Windows PowerShell
# Runs all Phase 0 GPU tests and saves results.

param(
    [Parameter(Mandatory=$true)]
    [string]$ModelRoot = "D:\AIModels",
    
    [string]$Precision = "fp8",
    
    [string[]]$Models = @("all")
)

Write-Host "Phase 0 GPU Test Kit — RTX 5090" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# Check if venv is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  WARNING: Virtual environment not activated" -ForegroundColor Yellow
    Write-Host "   Run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Environment check
Write-Host "Step 1: Environment Check" -ForegroundColor Green
Write-Host ("=" * 60)
python env_check.py --model-root $ModelRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Environment check failed. Fix issues before continuing." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Press Enter to continue with VRAM fit tests (or Ctrl+C to cancel)..."
Read-Host

# Step 2: VRAM fit tests
Write-Host ""
Write-Host "Step 2: VRAM Fit Tests" -ForegroundColor Green
Write-Host ("=" * 60)

$modelArgs = $Models -join " "
python vram_fit.py --model-root $ModelRoot --precision $Precision --models $modelArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "⚠️  VRAM fit tests encountered errors (check output above)" -ForegroundColor Yellow
}

# Step 3: Converter check (stub)
Write-Host ""
Write-Host "Step 3: Converter Check" -ForegroundColor Green
Write-Host ("=" * 60)
python converter_check.py --model-root $ModelRoot

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Phase 0 Tests Complete!" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Results saved to: phase0\results\*.json"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review results: ls phase0\results\*.json"
Write-Host "  2. Check samples: ls phase0\results\samples\"
Write-Host "  3. Commit results: git add phase0\results\*.json && git commit -m 'phase0: RTX 5090 results'"
Write-Host "  4. Push to GitHub: git push"
Write-Host ""
