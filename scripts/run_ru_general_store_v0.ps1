# ru-general store: frequency headwords → field → meta KB → remigrate → NCA (CUDA).
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

$store = 'lab/agent-stores/sss-ru-general-v0'
$kbFreq = 'lab/kb/kb-lexicon-frequency-ru-v1.json'

Write-Host '=== 0) Frequency headwords (DetCorpus CC0) ===' -ForegroundColor Green
python tools/fetch_ru_frequency_headwords_v0.py

Write-Host '=== 1) Init store (~50k lemmas) ===' -ForegroundColor Green
python tools/init_lexicon_store_v0.py --corpus-id ru-general --copies 3

Write-Host '=== 2) Meta: what frequency is and why (L3) ===' -ForegroundColor Green
python tools/ingest_kb_meta_l3_v0.py --store-dir $store --bundle $kbFreq --write

Write-Host '=== 3) L2 remigrate (once per vocabulary snapshot) ===' -ForegroundColor Green
python tools/remigrate_l2_lex_v0.py --store-dir $store `
    --out lab/exp_sss_v1/report_ru_general_remigrate.json

Write-Host '=== 4) NCA train all shards (CUDA) ===' -ForegroundColor Cyan
python tools/train_sss_nca_shards_v0.py `
    --store-dir $store `
    --layer all `
    --device cuda `
    --epochs 25 `
    --min-tokens 4

Write-Host '=== 5) Registry + manifest ===' -ForegroundColor Green
python tools/nca_stale_shards_v0.py --store-dir $store --sync-registry --dry-run
python tools/sss_memory_manifest_v0.py --store-dir $store --write

Write-Host "Done. Store: $store (overlap with Afan lemmas is expected; stores stay separate)." -ForegroundColor Green
