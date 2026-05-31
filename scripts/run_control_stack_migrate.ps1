# Control lattice stack: init lab store or migrate existing store.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/control-lab'
$bundle = 'lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json'

Write-Host '=== Init control-lab (bundle -> prism_control + ltm) ===' -ForegroundColor Green
python tools/init_control_lab.py --store-dir $store --bundle $bundle

Write-Host '=== Bench ===' -ForegroundColor Cyan
python tools/bench_control_stack.py --store-dir $store

Write-Host '=== Migrate all stores with field_state ===' -ForegroundColor Cyan
python tools/migrate_control_all_stores.py --export-ltm

Write-Host 'Done.' -ForegroundColor Green
