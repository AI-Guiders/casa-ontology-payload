# Phases A -> B -> C in order (SSS language lab)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-phases-abc'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$corpus = 'lab/text/corpus'
$exp = 'lab/exp_sss_v1'
$ncaOut = 'lab/nca_out_sss_l2_smoke'

Write-Host '========== PHASE A: corpus batch + growth + babble ==========' -ForegroundColor Green
python tools/gen_kb_bukvar_ru_full.py --out $bukvar
python tools/sss_field.py --store-dir $store --bundle $bukvar --listen-passes 2 --init

python tools/bench_sss_vocab_growth.py `
    --store-dir $store `
    --text lab/text/corpus/kolobok-excerpt.txt `
    --bukvar $bukvar `
    --out "$exp/report_abc_phase_a_growth.json"

python tools/sss_read_batch.py `
    --store-dir $store `
    --corpus-dir $corpus `
    --bukvar $bukvar `
    --listen-copies 2 `
    --out "$exp/report_abc_phase_a_batch.json"

Write-Host '========== PHASE B: char scan + W: field competition ==========' -ForegroundColor Green
python tools/sss_read_batch.py `
    --store-dir $store `
    --corpus-dir $corpus `
    --bukvar $bukvar `
    --listen-copies 2 `
    --field `
    --no-sleep `
    --out "$exp/report_abc_phase_b_field_batch.json"

python tools/sss_text_listen_field.py `
    --store-dir $store `
    --text lab/text/kolobok-excerpt.txt `
    --bukvar $bukvar `
    --out "$exp/report_abc_phase_b_kolobok_field.json"

Write-Host '========== PHASE C: NCA train + repair + sleep regrow hook ==========' -ForegroundColor Green
python tools/bench_sss_nca_repair.py `
    --store-dir $store `
    --train `
    --epochs 120 `
    --out-dir $ncaOut `
    --out "$exp/report_abc_phase_c_nca_repair.json"

Write-Host '=== set NCA model on state, sleep with regrow ===' -ForegroundColor Cyan
python tools/sss_sleep_nca_hook.py `
    --store-dir $store `
    --model "$ncaOut/model.pt" `
    --bukvar $bukvar `
    --text lab/text/corpus/kolobok-excerpt.txt

Write-Host 'All phases A-B-C done.' -ForegroundColor Green
