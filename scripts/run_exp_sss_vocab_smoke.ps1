# Vocabulary via text read-aloud (skazka primer)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/lexicon-vocab'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$skazka = 'lab/kb/kb-skazka-primer-v1.payload.json'
$session = 'lab/exp_lexicon_v1/skazka_read_session.json'
$probes = 'lab/exp_lexicon_v1/vocab_recall_probes.json'

Write-Host '=== bukvar + skazka KB ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bukvar
python tools/gen_kb_skazka_primer.py --out $skazka --session-out $session

Write-Host '=== init store (syllables listen) ===' -ForegroundColor Cyan
python tools/sss_field.py --store-dir $store --bundle $bukvar --listen-passes 2 --init
Copy-Item $skazka (Join-Path $store 'bundles/kb-skazka-primer-v1.payload.json')

Write-Host '=== Kolb segment (syllables ready) ===' -ForegroundColor Cyan
python tools/sss_kolb_cycle.py --store-dir $store --session lab/exp_lexicon_v1/kolb_segment_session.json --bundle $bukvar --out lab/exp_lexicon_v1/report_vocab_kolb.json | Out-Null

Write-Host '=== recall BEFORE read ===' -ForegroundColor Cyan
python tools/bench_sss_vocab.py --store-dir $store --probes $probes --out lab/exp_lexicon_v1/report_vocab_before.json

Write-Host '=== read story (text scenes) ===' -ForegroundColor Cyan
python tools/sss_read.py --store-dir $store --session $session --bundle $skazka --out lab/exp_lexicon_v1/report_vocab_read.json

Write-Host '=== recall AFTER read + sleep ===' -ForegroundColor Cyan
python tools/bench_sss_vocab.py --store-dir $store --probes $probes --out lab/exp_lexicon_v1/report_vocab_after.json

Write-Host 'Done.'
