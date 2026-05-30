# Fair compare at union vocab (162): bench windowed union vs monolith ONLY if model.pt exists.
# Monolithic union 1200ep on 64x64 is hours on 8GB — use -TrainMonolith for explicit long run.
param(
    [int]$Epochs = 1200,
    [switch]$TrainMonolith,
    [switch]$TrainMonolithOnly
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'examples/agent-stores/language-agent-lab-v0'
$grammar = "$store/bundles/kb-russian-language-rules-v1.bundle.v1.json"
$mre3 = "$store/bundles/kb-regex-mre3-ru-chapter-map-v1.bundle.v1.json"
$bundles = @($grammar, $mre3)
$reportDir = 'examples/exp_j_ru_v1'
$monoOut = 'examples/nca_out_exp_j_ru_union_full_v1'
$winOut = 'examples/nca_out_exp_j_ru_union_windowed_v1'
$monoModel = "$monoOut/model.pt"
$winModel = "$winOut/model.pt"

if ($TrainMonolith -and -not (Test-Path $monoModel)) {
    Write-Host '=== UNION monolithic train (aligned vocab 162) — LONG (hours) ===' -ForegroundColor Yellow
    $env:PYTHONUNBUFFERED = '1'
    $sw = [Diagnostics.Stopwatch]::StartNew()
    python tools/train_dmn_nca_multibundle.py `
        --bundles $bundles `
        --codec v3 --concept-mode section `
        --damage-mode patches --damage-patches 8 `
        --epochs $Epochs --save-model `
        --out-dir $monoOut
    $sw.Stop()
    Write-Host ("Monolithic train: {0:N1}s ({1:N2} min)" -f $sw.Elapsed.TotalSeconds, ($sw.Elapsed.TotalMinutes)) -ForegroundColor DarkGray
} elseif (Test-Path $monoModel) {
    Write-Host "Monolithic model exists: $monoModel" -ForegroundColor DarkGray
} else {
    Write-Host "Skip monolithic train (no model). Windowed union is canonical. Use -TrainMonolith for full 64x64 run." -ForegroundColor Yellow
}

if ($TrainMonolithOnly) {
    Write-Host 'TrainMonolithOnly — skipping benches.'
    exit 0
}

if (-not (Test-Path $winModel)) {
    throw "Windowed union model missing: $winModel"
}

if (Test-Path $monoModel) {
    python -c @"
import torch
from pathlib import Path
m=Path('$monoModel'); w=Path('$winModel')
cm=torch.load(m,map_location='cpu',weights_only=False); cw=torch.load(w,map_location='cpu',weights_only=False)
print('vocab monolith',len(cm['token_ids']),'windowed',len(cw['token_ids']))
if cm['token_ids']==cw['token_ids']:
    print('vocab aligned OK')
else:
    print('vocab MISMATCH — compare repair only within same checkpoint family')
"@
    Write-Host '=== repair bench monolith (162 vocab) ===' -ForegroundColor Cyan
    python tools/bench_windowed_repair.py --bundle $grammar --model $monoModel --codec v3 --concept-mode section `
        --out "$reportDir/report_fair_union_monolith_repair.json"
}

Write-Host '=== repair bench windowed union (162 vocab) ===' -ForegroundColor Cyan
python tools/bench_windowed_repair.py --bundle $grammar --model $winModel --codec v3 --concept-mode section `
    --out "$reportDir/report_fair_union_windowed_repair.json"

python tools/compare_exp_j_models.py --out "$reportDir/compare_fair_union_vocab.json"
Write-Host 'Done. Canonical checkpoint: union_windowed + model_hard.pt from windowed train.'
