# run_demo1.ps1 — one-click Demo1 launcher (Windows PowerShell)
# Usage:
#   .\run_demo1.ps1                       # self-test (510k) + ecosystem test + all cases
#   .\run_demo1.ps1 --case demo1/cases/case01_red_pma_process.json
#   .\run_demo1.ps1 --web                 # start minimal web UI on http://127.0.0.1:8765

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "..")   # cd into mvp/

Write-Host "== lgd-engine Demo1: 510(k) change gate + ecosystem ==" -ForegroundColor Cyan
Write-Host "python: $(python --version)"
Write-Host "cwd:    $(Get-Location)"
Write-Host ""

if ($args -contains "--web") {
    Write-Host "Starting web UI on http://127.0.0.1:8765  (Ctrl+C to stop)" -ForegroundColor Green
    python -m demo1.web
    exit $LASTEXITCODE
}

Write-Host "[1/3] Self-test: 510(k) change gate (test_demo1.py)..." -ForegroundColor Yellow
python -m demo1.test_demo1
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL test_demo1" -ForegroundColor Red; exit $LASTEXITCODE }
Write-Host ""

Write-Host "[2/3] Self-test: ecosystem (postmarket + jurisdiction FDA/NMPA)..." -ForegroundColor Yellow
python -m demo1.test_ecosystem
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL test_ecosystem" -ForegroundColor Red; exit $LASTEXITCODE }
Write-Host ""

Write-Host "[3/3] Running all 510(k) cases via CLI..." -ForegroundColor Yellow
if ($args.Count -gt 0) {
    python -m demo1.change_gate @args
} else {
    python -m demo1.change_gate --all
}
exit $LASTEXITCODE
