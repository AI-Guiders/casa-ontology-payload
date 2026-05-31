# Phase A: batch corpus read, vocab growth, babble from scene
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-phase-a'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$corpus = 'lab/text/corpus'
$exp = 'lab/exp_sss_v1'

Write-Host '=== init bukvar store ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bukvar
python tools/sss_field.py --store-dir $store --bundle $bukvar --listen-passes 2 --init

Write-Host '=== vocab growth pass1 vs pass2 (before batch) ===' -ForegroundColor Cyan
python tools/bench_sss_vocab_growth.py `
    --store-dir $store `
    --text lab/text/corpus/kolobok-excerpt.txt `
    --bukvar $bukvar `
    --out "$exp/report_phase_a_growth.json"

Write-Host '=== batch read corpus ===' -ForegroundColor Cyan
python tools/sss_read_batch.py `
    --store-dir $store `
    --corpus-dir $corpus `
    --bukvar $bukvar `
    --listen-copies 2 `
    --out "$exp/report_phase_a_batch.json"

Write-Host '=== babble scene p1 ===' -ForegroundColor Cyan
python tools/sss_vocab_surface.py `
    --store-dir $store `
    --scene-id p1 `
    --caption 'kolobok opening'

Write-Host 'Done Phase A.'
