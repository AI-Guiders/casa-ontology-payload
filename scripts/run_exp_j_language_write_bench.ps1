# Exp J phase B: write@sketch (articulation_grammar_v0) + grammar recall.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot '_kb_env.ps1')
Require-AgentNotesKb

$store = 'lab/agent-stores/language-agent-lab-v0'

Write-Host '=== sync language store (grammar + literacy) ===' -ForegroundColor Cyan
& (Join-Path $Root 'scripts\run_exp_j0_literacy_sync.ps1')

Write-Host '=== write@sketch (literacy + explain) ===' -ForegroundColor Cyan
python tools/bench_write_sketch.py `
    --queries lab/exp_j0_literacy/queries_write.jsonl `
    --store-dir $store `
    --out lab/exp_j0_literacy/report_write.json

Write-Host '=== write@sketch (grammar norm) ===' -ForegroundColor Cyan
python tools/bench_write_sketch.py `
    --queries lab/exp_j_ru_v1/queries_grammar.jsonl `
    --store-dir $store `
    --out lab/exp_j_ru_v1/report_write_grammar.json

Write-Host '=== grammar read@1 (substr in blocks) ===' -ForegroundColor Cyan
python tools/bench_answer_recall.py `
    --queries lab/exp_j_ru_v1/queries_grammar.jsonl `
    --store-dir $store `
    --out lab/exp_j_ru_v1/report_grammar_recall.json

Write-Host 'Done.'
