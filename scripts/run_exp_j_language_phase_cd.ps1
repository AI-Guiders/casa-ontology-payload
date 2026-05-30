# Exp J phases C+D: grammar recall gate + language windowed train.
param(
    [int]$TrainEpochs = 600,
    [switch]$SkipTrain
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $env:AGENT_NOTES_KB) {
    $env:AGENT_NOTES_KB = 'D:\experiments\agent-notes\knowledge'
}

Write-Host '========== PHASE C: sync + benches ==========' -ForegroundColor Magenta
& (Join-Path $Root 'scripts\run_exp_j_language_write_bench.ps1')

$recall = Get-Content 'examples/exp_j_ru_v1/report_grammar_recall.json' -Raw | ConvertFrom-Json
Write-Host ("grammar read@1 = {0}" -f $recall.answer_at_1) -ForegroundColor Yellow
if ($recall.answer_at_1 -lt 0.95) {
    Write-Host 'WARN: grammar recall below 0.95 — check report_grammar_recall.json' -ForegroundColor Red
}

if (-not $SkipTrain) {
    Write-Host '========== PHASE D: language windowed NCA ==========' -ForegroundColor Magenta
    & (Join-Path $Root 'scripts\run_exp_j_train_language_windowed.ps1') -Epochs $TrainEpochs
}

Write-Host '========== ALL DONE ==========' -ForegroundColor Green
