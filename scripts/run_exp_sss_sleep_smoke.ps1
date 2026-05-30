# SSS wake → hippo episode → sleep → memory stronger
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-lab-v0'
$bundle = 'lab/kb/kb-bukvar-ru-primer-v1.payload.json'
$episodes = 'lab/exp_sss_v1/sleep_smoke_episodes.json'

Write-Host '=== init memory cylinder ===' -ForegroundColor Cyan
python tools/sss_field.py --store-dir $store --bundle $bundle --listen-passes 5 --init

Write-Host '=== T_wake: babble + teacher (episode -> hippo) ===' -ForegroundColor Cyan
python tools/sss_wake_batch_v0.py --store-dir $store --episodes $episodes --bundle $bundle

Write-Host '=== votes before sleep (syllable.ma) ===' -ForegroundColor Cyan
python tools/bench_sss_sleep.py --store-dir $store --bundle $bundle --target lab/exp_sss_v1/sleep_smoke_target.json

Write-Host '=== T_sleep: consolidate ===' -ForegroundColor Cyan
python tools/sss_sleep_v0.py --store-dir $store --bundle $bundle

Write-Host '=== votes after sleep (syllable.ma) ===' -ForegroundColor Cyan
python tools/bench_sss_sleep.py --store-dir $store --bundle $bundle --target lab/exp_sss_v1/sleep_smoke_target.json

Write-Host '=== T_wake after sleep (babble) ===' -ForegroundColor Cyan
python tools/sss_surface_v0.py --store-dir $store --lattice L1_syllable --prompt-file lab/exp_sss_v1/sleep_smoke_cue.txt

Write-Host 'Done.'
