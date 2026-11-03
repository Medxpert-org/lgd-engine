# gate.ps1 — Windows PowerShell wrapper for gate_bot.py
# Usage:  powershell -ExecutionPolicy Bypass -File gate.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
python (Join-Path $here "gate_bot.py") --root $root
exit $LASTEXITCODE
