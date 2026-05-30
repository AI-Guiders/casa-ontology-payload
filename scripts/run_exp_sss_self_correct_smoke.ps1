# Self-correction: no external teacher; clusters emerge at learning
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'examples/agent-stores/sss-self-v0'
$bundle = 'examples/kb/kb-bukvar-ru-full-v1.payload.json'
$cues = 'examples/exp_sss_v1/self_correct_cues.json'

Write-Host '=== init (open syllables only in KB) ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle
python tools/sss_field.py --store-dir $store --bundle $bundle --listen-passes 2 --init

Write-Host '=== self-correct session + sleep + retry ===' -ForegroundColor Cyan
python tools/sss_self_correct_session_v0.py `
    --store-dir $store `
    --bundle $bundle `
    --cues $cues `
    --sleep-after `
    --retry

Write-Host 'Done.'
