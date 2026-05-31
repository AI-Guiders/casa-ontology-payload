# Immutable RU 33 + EN 26 alphabet → agent-core/alphabet + bench + optional NCA.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

Write-Host '=== Build core ltm (L0_grapheme) ===' -ForegroundColor Green
python tools/build_alphabet_core_ltm.py --train-nca --device cuda --epochs 80

Write-Host '=== Bench 33+26 ===' -ForegroundColor Cyan
python tools/bench_alphabet_core.py

Write-Host 'Done. Core: lab/agent-core/alphabet' -ForegroundColor Green
