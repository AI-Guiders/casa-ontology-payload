# Experiment F: module-masked cluster DMN (fMRI-style parcels)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Build kb-modules manifest ===" -ForegroundColor Cyan
python tools/build_kb_modules.py

Write-Host "=== Experiment F: module-aware cluster train + bench ===" -ForegroundColor Cyan
# One experiment at a time; auto batch=24 on GPU (see nca_train_util.py)
python tools/exp_f_modules.py --epochs 600 --seeds 15 --out-root examples/exp_f_modules_v2_gpu
python tools/compare_exp_ef.py --f examples/exp_f_modules_v2_gpu/report.json

Write-Host "Done. See examples/exp_f_modules_v1/report.json"
