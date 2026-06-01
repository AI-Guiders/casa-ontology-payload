# ru-general store: frequency headwords → field → meta KB → remigrate → NCA (CUDA).
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

$store = 'lab/agent-stores/lexicon-ru-general'
$kbFreq = 'lab/kb/kb-lexicon-frequency-ru-v1.json'

Write-Host '=== 0) Frequency headwords (DetCorpus CC0) ===' -ForegroundColor Green
python tools/fetch_ru_frequency_headwords.py

Write-Host '=== 1) Init store (~50k lemmas) ===' -ForegroundColor Green
python tools/init_lexicon_store.py --corpus-id ru-general --copies 3

Write-Host '=== 2) Meta: what frequency is and why (L3) ===' -ForegroundColor Green
python tools/ingest_kb_meta_l3.py --store-dir $store --bundle $kbFreq --write

Write-Host '=== 3) L2 remigrate (once per vocabulary snapshot) ===' -ForegroundColor Green
python tools/remigrate_l2_lex.py --store-dir $store `
    --out lab/exp_lexicon_v1/report_ru_general_remigrate.json

Write-Host '=== 4) NCA train all shards (CUDA) ===' -ForegroundColor Cyan
python tools/train_sss_nca_shards.py `
    --store-dir $store `
    --layer all `
    --device cuda `
    --epochs 25 `
    --min-tokens 4

Write-Host '=== 5) Registry + manifest ===' -ForegroundColor Green
python tools/nca_stale_shards.py --store-dir $store --sync-registry --dry-run
python tools/lexicon_memory_manifest.py --store-dir $store --write

Write-Host "Done. Store: $store (overlap with Afan lemmas is expected; stores stay separate)." -ForegroundColor Green
