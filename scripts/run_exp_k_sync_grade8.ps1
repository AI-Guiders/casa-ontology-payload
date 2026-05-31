# Exp K phase 1: sync grade-8 C# KB (+ guess-number) into code-agent store, K0 bench.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot '_kb_env.ps1')
Require-AgentNotesKb

$manifest = 'manifests/kb-bundles-csharp-grade8-v1.json'
$store = 'lab/agent-stores/code-agent-lab-v0'
$card = 'lab/agent-cards/research-agent.v0.json'

function Sync-Doc {
    param([string]$MdAbs, [string]$DocPath, [string]$OutBundle)
    Write-Host "=== sync $DocPath ===" -ForegroundColor Cyan
    python tools/kb_sync.py `
        --manifest $manifest `
        --md $MdAbs `
        --doc-path $DocPath `
        --out $OutBundle `
        --import-to $store `
        --agent-card $card `
        --tier easy
}

$grade8Md = Join-Path $env:AGENT_NOTES_KB 'worlds\software-dotnet-csharp\kb-csharp-console-grade8-v1.md'
Sync-Doc -MdAbs $grade8Md `
    -DocPath 'worlds/software-dotnet-csharp/kb-csharp-console-grade8-v1.md' `
    -OutBundle 'lab/kb/kb-csharp-console-grade8.bundle.v1.json'

$guessMd = Join-Path $Root 'lab\kb\kb-csharp-guess-number-canonical.md'
Sync-Doc -MdAbs $guessMd `
    -DocPath 'lab/kb/kb-csharp-guess-number-canonical.md' `
    -OutBundle 'lab/kb/kb-csharp-guess-number-canonical.bundle.v1.json'

Write-Host '=== rebuild union field ===' -ForegroundColor Cyan
python tools/rebuild_agent_store.py --store-dir $store

Write-Host '=== K0 bench grade8 queries ===' -ForegroundColor Cyan
python tools/bench_answer_recall.py `
    --queries lab/exp_k_grade8/queries.jsonl `
    --store-dir $store `
    --out lab/exp_k_grade8/report_k0_recall.json

Write-Host '=== sample infer ===' -ForegroundColor Cyan
python tools/sn_cen_infer.py --from-field --store-dir $store `
    --query "напиши консольную программу сумма двух чисел C# TryParse"

Write-Host 'Done.'
