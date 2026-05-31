# Afan-I verify: lattice (grapheme/syllable/word) + corpus word/punct coverage
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-afan'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$stack = 'design/prisms/memory/stack.json'
$corpus = 'lab/text/corpus/afanasyev'
$outDir = 'lab/exp_sss_v1'

Write-Host '=== Afan-I: lattice (L0 grapheme, L1 syllable, L2 word) ===' -ForegroundColor Cyan
python tools/bench_sss_lattice.py `
    --store-dir $store `
    --bundle $bundle `
    --stack $stack `
    --out "$outDir/report_afan_lattice.json"

Write-Host '=== Afan-I: corpus word + punct coverage (624 tales) ===' -ForegroundColor Cyan
python tools/bench_sss_corpus_coverage.py `
    --store-dir $store `
    --corpus-dir $corpus `
    --out "$outDir/report_afan_corpus_coverage.json"

Write-Host '=== Afan-I: kolobok excerpt spot-check ===' -ForegroundColor Cyan
python tools/bench_sss_text_ingest.py `
    --store-dir $store `
    --text lab/text/kolobok-excerpt.txt `
    --out "$outDir/report_afan_kolobok_spot.json"

Write-Host 'Done. Reports in' $outDir
