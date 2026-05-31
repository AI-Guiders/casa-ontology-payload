# Real tale text ingest: auto word extract, no punctuation, no pre-labeled cards
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-text'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$tale = 'lab/text/kolobok-excerpt.txt'
$dynamic = 'lab/kb/kb-kolobok-excerpt-dynamic.payload.json'

Write-Host '=== init bukvar (syllables) ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bukvar
python tools/sss_field.py --store-dir $store --bundle $bukvar --listen-passes 2 --init

Write-Host '=== coverage BEFORE tale ===' -ForegroundColor Cyan
python tools/bench_sss_text_ingest.py --store-dir $store --text $tale --out lab/exp_sss_v1/report_text_ingest_before.json

Write-Host '=== ingest kolobok excerpt ===' -ForegroundColor Cyan
python tools/sss_text_ingest.py `
    --store-dir $store `
    --text $tale `
    --bukvar $bukvar `
    --save-bundle $dynamic `
    --out lab/exp_sss_v1/report_text_ingest_kolobok.json

Write-Host '=== coverage AFTER tale ===' -ForegroundColor Cyan
python tools/bench_sss_text_ingest.py --store-dir $store --text $tale --out lab/exp_sss_v1/report_text_ingest_after.json

Write-Host 'Done.'
