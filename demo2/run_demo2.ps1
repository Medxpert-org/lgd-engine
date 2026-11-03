# Demo2 一键运行脚本 — 五席医械门禁评审会
# 用法: .\run_demo2.ps1              # 普通案例自动跑
#       .\run_demo2.ps1 critical    # critical 案例自动跑（触发 hold）
#       .\run_demo2.ps1 test        # 只跑自测

param(
    [string]$mode = "normal"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$demoPkgDir = $scriptDir           # demo2 包目录
$parentDir = Split-Path -Parent $scriptDir   # mvp 上级目录（python -m 从这里跑）
Set-Location $parentDir

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "  Demo2 五席医械门禁评审会 — 一键运行" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan

switch ($mode.ToLower()) {
    "test" {
        Write-Host "`n[模式] 自测`n" -ForegroundColor Yellow
        python "$demoPkgDir\test_demo2.py"
        exit $LASTEXITCODE
    }
    "critical" {
        $caseFile = "demo2\case_gate_report_critical.json"
        Write-Host "`n[模式] critical 案例（触发 hold）`n" -ForegroundColor Yellow
    }
    default {
        $caseFile = "demo2\case_gate_report.json"
        Write-Host "`n[模式] 普通案例`n" -ForegroundColor Yellow
    }
}

Write-Host "运行: python -m demo2.session --case $caseFile --auto`n" -ForegroundColor Gray
python -m demo2.session --case $caseFile --auto
$exitCode = $LASTEXITCODE

Write-Host "`n────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "退出码: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })

# Show recent events
$eventsPath = "$demoPkgDir\events.jsonl"
if (Test-Path $eventsPath) {
    Write-Host "`n最近 5 条事件流摘录:" -ForegroundColor DarkGray
    Get-Content $eventsPath -Tail 5 | ForEach-Object {
        $obj = $_ | ConvertFrom-Json
        Write-Host "  [$($obj.type)] $($obj.author) @ $($obj.timestamp)" -ForegroundColor DarkGray
    }
}

# Show DB summary
$dbPath = "$demoPkgDir\decisions_demo.db"
if (Test-Path $dbPath) {
    Write-Host "`n决议库记录数:" -ForegroundColor DarkGray
    python -c "import sqlite3; c=sqlite3.connect(r'$dbPath'); print('  ', c.execute('SELECT COUNT(*) FROM decisions').fetchone()[0], '条')"
}

exit $exitCode
