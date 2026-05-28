# E: cluster DMN + per-cluster digest/gate + infer samples
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:AGENT_NOTES_KB = "d:\Experiments\agent-notes\knowledge"
python tools/build_kb_bundles.py --per-doc-graph --kb-root $env:AGENT_NOTES_KB

Write-Host "=== Experiment E: cluster DMN ===" -ForegroundColor Cyan
python tools/exp_e_cluster_dmn.py --epochs 800 --seeds 20

Write-Host "=== Layered digest + gate per cluster ===" -ForegroundColor Cyan
python tools/train_layered_cluster.py --digest-epochs 250 --gate-epochs 250

Write-Host "=== Infer samples ===" -ForegroundColor Cyan
python tools/layered_infer.py --bundle examples/kb-perdoc/research-ml.bundle.v1.json --cluster research --out examples/layered_out/infer_research_cluster.json
python tools/layered_infer.py --bundle examples/kb-perdoc/casa-goals.bundle.v1.json --cluster goals --out examples/layered_out/infer_goals_cluster.json

Write-Host "Done."
