# Experiment K phase 0: sync C# lab KB + answer recall (K0). Emit/build — phase 3.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $env:AGENT_NOTES_KB) {
    $env:AGENT_NOTES_KB = 'D:\experiments\agent-notes\knowledge'
}

$manifest = 'manifests/kb-bundles-csharp-lab-v0.json'
$store = 'lab/agent-stores/code-agent-lab-v0'
$card = 'lab/agent-cards/research-agent.v0.json'
$doc = 'kb-csharp-guess-number-canonical'

Write-Host '=== Exp K: sync csharp lab KB ===' -ForegroundColor Cyan
$md = Join-Path $Root 'lab/kb/kb-csharp-guess-number-canonical.md'
python tools/kb_sync.py `
    --manifest $manifest `
    --md $md `
    --doc-path lab/kb/kb-csharp-guess-number-canonical.md `
    --import-to $store `
    --agent-card $card `
    --tier easy

Write-Host '=== rebuild union field ===' -ForegroundColor Cyan
python tools/rebuild_agent_store.py --store-dir $store

Write-Host '=== K0 bench answer recall ===' -ForegroundColor Cyan
python tools/bench_answer_recall.py `
    --queries lab/exp_k_guess_number/queries.jsonl `
    --store-dir $store `
    --out lab/exp_k_guess_number/report_k0_recall.json

Write-Host '=== sample infer ===' -ForegroundColor Cyan
python tools/sn_cen_infer.py --from-field --store-dir $store `
    --query "C# игра угадай число больше меньше"

Write-Host 'Done. Next: phase 1 expand KB, phase 3 tools/bench_exp_k_emit.py'
