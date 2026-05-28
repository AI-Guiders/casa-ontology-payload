# Experiment F: module-masked cluster DMN (fMRI-style parcels)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Build kb-modules manifest ===" -ForegroundColor Cyan
python tools/build_kb_modules.py

Write-Host "=== Experiment F: module-aware cluster train + bench ===" -ForegroundColor Cyan
python tools/exp_f_modules.py --epochs 600 --seeds 15

Write-Host "Done. See examples/exp_f_modules_v1/report.json"
