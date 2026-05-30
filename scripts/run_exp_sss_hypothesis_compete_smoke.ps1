# Multi-hypothesis H: competition on field (before / after Kolb)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'examples/agent-stores/sss-hypothesis-v0'
$bundle = 'examples/kb/kb-bukvar-ru-full-v1.payload.json'

Write-Host '=== init ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle
python tools/sss_field.py --store-dir $store --bundle $bundle --listen-passes 2 --init

Write-Host '=== compete (no rule yet) ===' -ForegroundColor Cyan
python tools/bench_sss_hypothesis_compete.py --store-dir $store --out examples/exp_sss_v1/report_hypothesis_compete_before.json

Write-Host '=== Kolb internal reconcile + sleep ===' -ForegroundColor Cyan
python tools/sss_kolb_cycle_v0.py --store-dir $store --session examples/exp_sss_v1/kolb_segment_session.json --bundle $bundle --out examples/exp_sss_v1/report_hypothesis_compete_kolb.json

Write-Host '=== compete after rule on field ===' -ForegroundColor Cyan
python tools/bench_sss_hypothesis_compete.py --store-dir $store --out examples/exp_sss_v1/report_hypothesis_compete_after.json

Write-Host 'Done.'
