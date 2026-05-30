# More spatial tiles (stride 8) + GPU window-batch sweep.
param(
    [int]$SweepEpochs = 40,
    [int]$StrideTrainEpochs = 120
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUNBUFFERED = '1'

$grammar = 'examples/agent-stores/language-agent-lab-v0/bundles/kb-russian-language-rules-v1.bundle.v1.json'
$bundles = @(
    $grammar,
    'examples/agent-stores/language-agent-lab-v0/bundles/kb-regex-mre3-ru-chapter-map-v1.bundle.v1.json'
)

Write-Host '=== GPU windows_per_batch sweep (union bundles, short) ===' -ForegroundColor Cyan
python tools/bench_window_batch_sweep.py `
    --bundle $grammar `
    --epochs $SweepEpochs `
    --batches 24 32 40 48 `
    --out examples/exp_j_ru_v1/bench_window_batch_sweep.json

Write-Host '=== Union windowed stride=8 (more tiles), 120 ep, B=40 ===' -ForegroundColor Cyan
python tools/train_dmn_nca_windowed.py `
    --bundles $bundles `
    --codec v3 --concept-mode section `
    --tile-w 32 --tile-h 32 --stride-x 8 --stride-y 8 --ghost 2 `
    --windows-per-batch 40 --max-windows-per-batch 48 `
    --damage-mode patches --damage-patches 6 `
    --epochs $StrideTrainEpochs --save-model `
    --out-dir examples/nca_out_exp_j_ru_union_windowed_s8_v1

Write-Host 'Done.'
