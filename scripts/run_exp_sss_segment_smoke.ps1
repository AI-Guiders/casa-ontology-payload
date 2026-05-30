# Hypothesis → gentle rule correction → sleep → generalize segment
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-segment-v0'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$heldout = 'lab/exp_sss_v1/segment_heldout_words.json'
$train = 'lab/exp_sss_v1/segment_train_vstrecha.json'

Write-Host '=== init ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle
python tools/sss_field.py --store-dir $store --bundle $bundle --listen-passes 2 --init

Write-Host '=== teach rule + sleep + held-out ===' -ForegroundColor Cyan
python tools/run_segment_smoke_v0.py `
    --store-dir $store `
    --bundle $bundle `
    --train $train `
    --heldout $heldout `
    --out lab/exp_sss_v1/report_segment_generalize.json

Write-Host 'Done.'
