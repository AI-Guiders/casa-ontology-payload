# Sleep semantic ingest v0 — entity hub + taxonomy + POS claims (L3), no NCA.
# Run from casa-ontology-payload/: .\scripts\run_sleep_semantic_ingest.ps1

param(
    [string]$StoreDir = "lab/agent-stores/lexicon-ru-general",
    [switch]$DryRun,
    [switch]$SeedOnly
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:PYTHONUTF8 = "1"
$EntityBundle = "lab/exp_bilingual/kb-entity-surfaces-dev.v1.json"
$TaxonomyBundle = "lab/kb/kb-entity-taxonomy-v1.json"
$PosBundle = if ($SeedOnly) { "lab/kb/ru-pos-seed-v1.json" } else { "lab/kb/ru-pos-detcorpus-v1.json" }
$ReportDir = "lab/exp_bilingual/reports"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

$writeFlag = if ($DryRun) { @() } else { @("--write") }

if (-not $SeedOnly -and -not (Test-Path $PosBundle)) {
    Write-Host "Building POS bundle (UD + DetCorpus) …" -ForegroundColor Yellow
    python tools/fetch_ud_lemma_pos.py --locale ru
    python tools/build_pos_bundle.py --locale ru --top-n 8000
}

Write-Host "=== entity hub ingest ===" -ForegroundColor Cyan
python tools/entity_hub_ingest.py --store-dir $StoreDir --bundle $EntityBundle @writeFlag

Write-Host "=== entity taxonomy ingest ===" -ForegroundColor Cyan
python tools/entity_taxonomy_ingest.py --store-dir $StoreDir --bundle $TaxonomyBundle @writeFlag

Write-Host "=== POS claims ingest ===" -ForegroundColor Cyan
python tools/pos_claims_ingest.py --store-dir $StoreDir --bundle $PosBundle @writeFlag

Write-Host "=== bench entity hub ===" -ForegroundColor Cyan
python tools/bench_entity_hub.py --store-dir $StoreDir --bundle $EntityBundle `
    --out "$ReportDir/sleep_entity_hub.json" 2>&1 | Select-Object -Last 1

Write-Host "=== bench entity taxonomy ===" -ForegroundColor Cyan
python tools/bench_entity_taxonomy.py --store-dir $StoreDir `
    --out "$ReportDir/sleep_entity_taxonomy.json" 2>&1 | Select-Object -Last 1

Write-Host "=== bench POS claims (sample) ===" -ForegroundColor Cyan
python tools/bench_pos_claims.py --store-dir $StoreDir --bundle $PosBundle `
    --max-cues 200 `
    --out "$ReportDir/sleep_pos_claims.json" 2>&1 | Select-Object -Last 1

if ($DryRun) {
    Write-Host "DryRun: no field_state write" -ForegroundColor Yellow
} else {
    Write-Host "Written: $StoreDir/field_state.json" -ForegroundColor Green
}
