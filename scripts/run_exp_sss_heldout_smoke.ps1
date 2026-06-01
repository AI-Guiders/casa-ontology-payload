# Held-out bench + auto-episode + sleep (train only on ma)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/lexicon-heldout'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$train = 'lab/exp_lexicon_v1/train_ma_only.json'
$heldout = 'lab/exp_lexicon_v1/heldout_syllables.json'
$stack = 'design/prisms/memory/stack.json'

Write-Host '=== generate bundle + init ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle
python tools/sss_field.py --store-dir $store --bundle $bundle --stack $stack --listen-passes 5 --init

Write-Host '=== held-out BEFORE train ===' -ForegroundColor Cyan
python tools/bench_sss_heldout.py `
    --store-dir $store `
    --bundle $bundle `
    --cases $heldout `
    --out lab/exp_lexicon_v1/report_heldout_before.json

Write-Host '=== train: only ma (auto-episode if wrong) ===' -ForegroundColor Cyan
python tools/sss_wake_batch.py --store-dir $store --episodes $train --bundle $bundle --auto

Write-Host '=== sleep ===' -ForegroundColor Cyan
python tools/sss_sleep.py --store-dir $store --bundle $bundle

Write-Host '=== held-out AFTER train+sleep ===' -ForegroundColor Cyan
python tools/bench_sss_heldout.py `
    --store-dir $store `
    --bundle $bundle `
    --cases $heldout `
    --out lab/exp_lexicon_v1/report_heldout_after.json

Write-Host '=== votes: trained ma vs held-out pa ===' -ForegroundColor Cyan
python tools/bench_sss_sleep.py --store-dir $store --bundle $bundle --target lab/exp_lexicon_v1/sleep_smoke_target.json
python tools/bench_sss_sleep.py --store-dir $store --bundle $bundle --target lab/exp_lexicon_v1/heldout_target_pa.json

Write-Host 'Done.'
