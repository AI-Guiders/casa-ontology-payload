# Exp B0: bukvar primer — layered DMN, listen, babble from field (no CEN claims).
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'examples/agent-stores/bukvar-lab-v0'
$bundle = 'examples/kb/kb-bukvar-ru-primer-v1.payload.json'
$layout = 'design/layout.v1.json'

Write-Host '=== B0: init store + listen (3 passes) ===' -ForegroundColor Cyan
python tools/bukvar_field.py --store-dir $store --bundle $bundle --layout $layout --listen-passes 5 --init

Write-Host '=== B0: coverage (layers in cylinder) ===' -ForegroundColor Cyan
python tools/bench_bukvar_coverage.py `
    --store-dir $store `
    --bundle $bundle `
    --layout $layout `
    --out examples/exp_b0_bukvar/report_coverage.json

Write-Host '=== B0: babble B0 (graphemes) ===' -ForegroundColor Cyan
python tools/bukvar_babble_v0.py --store-dir $store --layout $layout --layer B0 --prompt 'м а'

Write-Host '=== B0: babble B1 (syllables) ===' -ForegroundColor Cyan
python tools/bukvar_babble_v0.py --store-dir $store --layout $layout --layer B1 --prompt 'ма'

Write-Host '=== B0: babble B2 (words) ===' -ForegroundColor Cyan
python tools/bukvar_babble_v0.py --store-dir $store --layout $layout --layer B2 --prompt 'мама'

Write-Host 'Done. Store:' $store
