# Russian lexicon store: lex remigrate, manifest, NCA (CUDA), optional sleep.
# Corpus sources (Afan, bukvar, …) are ingest metadata only — not store layout names.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

$ingestRef = 'lab/agent-stores/sss-afan'
$store = 'lab/agent-stores/sss-ru-lexicon'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$exp = 'lab/exp_sss_v1'

Write-Host '=== 0) Ensure store (copy monolith once from ingest ref) ===' -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $store | Out-Null
$dst = Join-Path $store 'field_state.json'
if (-not (Test-Path $dst)) {
    Copy-Item (Join-Path $ingestRef 'field_state.json') $dst
    Write-Host "Copied -> $dst"
}

Write-Host '=== 1) L2 remigrate (corpus_quantile lex plan) ===' -ForegroundColor Green
python tools/remigrate_l2_lex.py `
    --store-dir $store `
    --out "$exp/report_ru_lexicon_remigrate.json"

Write-Host '=== 2) Memory map ===' -ForegroundColor Green
python tools/sss_memory_manifest.py `
    --store-dir $store `
    --compare-dir $ingestRef `
    --write `
    | Tee-Object -FilePath "$exp/report_ru_lexicon_memory_manifest.json"

Write-Host '=== 3) NCA train (weights -> store/nca/<lattice>/) ===' -ForegroundColor Green
python tools/train_sss_nca_shards.py `
    --store-dir $store `
    --layer all `
    --device cuda `
    --max-tokens 4096 `
    --min-tokens 4 `
    2>&1 | Tee-Object -FilePath "$exp/nca_train_ru_lexicon_cuda.log"

Write-Host '=== 4) Sleep + NCA regrow ===' -ForegroundColor Green
python tools/sss_sleep_all_nca.py `
    --store-dir $store `
    --bundle $bukvar `
    --device cuda `
    | Tee-Object -FilePath "$exp/report_ru_lexicon_sleep_nca.json"

Write-Host '=== 5) Final manifest ===' -ForegroundColor Green
python tools/sss_memory_manifest.py --store-dir $store --write

Write-Host "Done. Store: $store/  NCA: $store/nca/  Map: $store/MEMORY.md"
