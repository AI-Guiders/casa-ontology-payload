# Full Cyrillic B0 + SSS lattice coverage
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/lexicon-full'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$stack = 'design/prisms/memory/stack.json'

Write-Host '=== generate full bukvar bundle ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle

Write-Host '=== init store (listen) ===' -ForegroundColor Cyan
python tools/sss_field.py --store-dir $store --bundle $bundle --stack $stack --listen-passes 2 --init

Write-Host '=== lattice coverage (33 graphemes) ===' -ForegroundColor Cyan
python tools/bench_sss_lattice.py `
    --store-dir $store `
    --bundle $bundle `
    --stack $stack `
    --out lab/exp_lexicon_v1/report_full_lattice.json

Write-Host 'Done. Store:' $store
