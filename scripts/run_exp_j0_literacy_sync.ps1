# Exp J0: literacy KB (read/write RU) + full language store union + read benches.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot '_kb_env.ps1')
Require-AgentNotesKb

$store = 'lab/agent-stores/language-agent-lab-v0'
$card = 'lab/agent-cards/research-agent.v0.json'

Write-Host '=== Exp J0: sync grammar + literacy (language store) ===' -ForegroundColor Cyan
& (Join-Path $Root 'scripts\run_exp_j_language_sync.ps1')

$literacyMd = Join-Path $env:AGENT_NOTES_KB 'worlds\evidence-humanities-shelf\kb-russian-literacy-agent-v1.md'
Write-Host '=== sync literacy ===' -ForegroundColor Cyan
python tools/kb_sync.py `
    --manifest manifests/kb-bundles-russian-literacy-v1.json `
    --md $literacyMd `
    --doc-path worlds/evidence-humanities-shelf/kb-russian-literacy-agent-v1.md `
    --out lab/kb/kb-russian-literacy-agent.bundle.v1.json `
    --import-to $store `
    --agent-card $card `
    --tier easy

Write-Host '=== rebuild union field ===' -ForegroundColor Cyan
python tools/rebuild_agent_store.py --store-dir $store

Write-Host '=== read@1 direct ===' -ForegroundColor Cyan
python tools/bench_answer_recall.py `
    --queries lab/exp_j0_literacy/queries_read.jsonl `
    --store-dir $store `
    --out lab/exp_j0_literacy/report_read.json

Write-Host '=== read@1 paraphrase ===' -ForegroundColor Cyan
python tools/bench_answer_recall.py `
    --queries lab/exp_j0_literacy/queries_paraphrase.jsonl `
    --store-dir $store `
    --out lab/exp_j0_literacy/report_paraphrase.json

Write-Host 'Done. See lab/exp_j0_literacy/report_*.json'
