# Afanasyev corpus: sanitize → audit → batch ingest (field + punct)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/ingest-ref-afan'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$corpus = 'lab/text/corpus/afanasyev'
$exp = 'lab/exp_lexicon_v1'

Write-Host '=== sanitize corpus (OCR/editorial) ===' -ForegroundColor Cyan
python tools/sanitize_afanasyev_corpus.py --corpus-dir $corpus `
    --out "$exp/report_afanasyev_sanitize.json"

Write-Host '=== audit after sanitize ===' -ForegroundColor Cyan
python tools/audit_afanasyev_corpus.py --corpus-dir $corpus `
    --out "$exp/report_afanasyev_audit_after_sanitize.json"

Write-Host '=== init bukvar store ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bukvar
python tools/sss_field.py --store-dir $store --bundle $bukvar --listen-passes 2 --init

Write-Host '=== batch ingest 624 tales (field + punct, listen x1) ===' -ForegroundColor Cyan
python tools/sss_read_batch.py `
    --store-dir $store `
    --corpus-dir $corpus `
    --bukvar $bukvar `
    --listen-copies 1 `
    --field `
    --resume `
    --checkpoint-every 0 `
    --out "$exp/report_afanasyev_ingest_batch.json"

Write-Host '=== punct coverage sample ===' -ForegroundColor Cyan
python tools/bench_sss_text_ingest.py `
    --store-dir $store `
    --text lab/text/corpus/afanasyev/afan-v1-n001.txt `
    --out "$exp/report_afanasyev_punct_after_ingest.json"

Write-Host 'Done Afanasyev ingest.'
