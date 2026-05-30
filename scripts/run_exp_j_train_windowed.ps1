# Experiment J — windowed NCA train (tile + planner v0) + benches + compare.
param(
    [switch]$Union,
    [int]$Epochs = 400,
    [int]$Seeds = 20,
    [switch]$SkipCompare
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'examples/agent-stores/language-agent-lab-v0'
$grammar = "$store/bundles/kb-russian-language-rules-v1.bundle.v1.json"
$mre3 = "$store/bundles/kb-regex-mre3-ru-chapter-map-v1.bundle.v1.json"

if ($Union) {
    $bundles = @($grammar, $mre3)
    $tag = 'union'
    $outDir = 'examples/nca_out_exp_j_ru_union_windowed_v1'
} else {
    $bundles = @($grammar)
    $tag = 'grammar'
    $outDir = 'examples/nca_out_exp_j_ru_windowed_v1'
}

$reportDir = 'examples/exp_j_ru_v1'

Write-Host "=== Exp J WINDOWED train ($tag) epochs=$Epochs ===" -ForegroundColor Cyan
$env:PYTHONUNBUFFERED = '1'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
python tools/train_dmn_nca_windowed.py `
    --bundles $bundles `
    --codec v3 --concept-mode section `
    --tile-w 32 --tile-h 32 --stride-x 16 --stride-y 16 --ghost 2 `
    --windows-per-batch 0 `
    --damage-mode patches --damage-patches 6 `
    --epochs $Epochs --save-model `
    --out-dir $outDir

$model = "$outDir/model.pt"
if (-not (Test-Path $model)) {
    throw "Training did not produce $model"
}

$sw.Stop()
$trainSec = $sw.Elapsed.TotalSeconds
Write-Host ("Train wall-clock: {0:N1}s ({1:N2} min)" -f $trainSec, ($trainSec / 60)) -ForegroundColor DarkGray

$ckptDir = "$store/checkpoints"
New-Item -ItemType Directory -Force -Path $ckptDir | Out-Null
Copy-Item -Force $model "$ckptDir/model_hard.pt"
Write-Host "Checkpoint: $ckptDir/model_hard.pt"

Write-Host '=== bench monolithic vs windowed repair (grammar) ===' -ForegroundColor Cyan
python tools/bench_windowed_repair.py `
    --bundle $grammar `
    --model $model `
    --codec v3 --concept-mode section `
    --out "$reportDir/report_windowed_repair_${tag}.json"

if ($Epochs -ge 200) {
    $curveOut = "$reportDir/curve_${tag}_windowed_s${Seeds}.json"
    Write-Host "=== damage curve 0.10..0.60 seeds=$Seeds ===" -ForegroundColor Cyan
    python tools/bench_curve_dmn_nca_union.py `
        --bundle $grammar `
        --model $model `
        --codec v3 --concept-mode section `
        --damage-mode patches --damage-patches 8 `
        --damages "0.10,0.20,0.25,0.30,0.40,0.50,0.60" `
        --seeds $Seeds `
        --out $curveOut

    Write-Host '=== answer field vs repair ===' -ForegroundColor Cyan
    python tools/bench_exp_j_repair_answer.py `
        --queries examples/exp_j_ru_queries.jsonl `
        --store-dir $store --model $model `
        --out "$reportDir/report_repair_${tag}_windowed.json"
}

if (-not $SkipCompare) {
    Write-Host '=== compare grammar_full vs union_windowed ===' -ForegroundColor Cyan
    python tools/compare_exp_j_models.py `
        --out "$reportDir/compare_grammar_full_vs_union_windowed.json"
}

Write-Host "Done. model=$model"
