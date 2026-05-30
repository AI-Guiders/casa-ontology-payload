# Experiments A -> B -> C (ontology-in-field lab v1)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m pip install -q -r tools/requirements.txt

$env:AGENT_NOTES_KB = "d:\Experiments\agent-notes\knowledge"
python tools/build_kb_bundles.py --kb-root $env:AGENT_NOTES_KB

Write-Host "=== Experiment A: KB scale ===" -ForegroundColor Cyan
python tools/exp_a_kb_scale.py --epochs 1200 --seeds 20

$modelA = "lab/exp_a_kb_scale_v1/model.pt"

Write-Host "=== Experiment B: decode sweep ===" -ForegroundColor Cyan
python tools/exp_b_decode_sweep.py --model $modelA

Write-Host "=== Experiment C: goal-3 grid ===" -ForegroundColor Cyan
python tools/exp_c_goal3_grid.py --model $modelA

Write-Host "Done. Reports: lab/exp_a_kb_scale_v1/report.json, exp_b_decode_sweep_v1/report.json, exp_c_goal3_grid_v1/report.json"
