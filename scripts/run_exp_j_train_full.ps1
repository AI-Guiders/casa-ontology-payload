# Experiment J — full train: 1200 epochs + damage curve (20 seeds) + answer bench.
# Default: grammar-only (modern RU). Pass -Union to include MRE3 in union vocab.
param(
    [switch]$Union,
    [int]$Epochs = 1200,
    [int]$Seeds = 20
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'lab/agent-stores/language-agent-lab-v0'
$grammar = "$store/bundles/kb-russian-language-rules-v1.bundle.v1.json"
$mre3 = "$store/bundles/kb-regex-mre3-ru-chapter-map-v1.bundle.v1.json"

if ($Union) {
    $bundles = @($grammar, $mre3)
    $outDir = 'lab/nca_out_exp_j_ru_union_full_v1'
    $tag = 'union'
} else {
    $bundles = @($grammar)
    $outDir = 'lab/nca_out_exp_j_ru_grammar_full_v1'
    $tag = 'grammar'
}

Write-Host "=== Exp J FULL train ($tag) epochs=$Epochs ===" -ForegroundColor Cyan
python tools/train_dmn_nca_multibundle.py `
    --bundles $bundles `
    --codec v3 --concept-mode section `
    --damage-mode patches --damage-patches 8 `
    --epochs $Epochs --save-model `
    --out-dir $outDir

$model = "$outDir/model.pt"
$ckptDir = "$store/checkpoints"
New-Item -ItemType Directory -Force -Path $ckptDir | Out-Null
Copy-Item -Force $model "$ckptDir/model_hard.pt"
Write-Host "Checkpoint: $ckptDir/model_hard.pt"

$curveOut = "lab/exp_j_ru_v1/curve_${tag}_s${Seeds}.json"
Write-Host "=== damage curve 0.10..0.60 seeds=$Seeds ===" -ForegroundColor Cyan
python tools/bench_curve_dmn_nca_union.py `
    --bundle $grammar `
    --model $model `
    --codec v3 --concept-mode section `
    --damage-mode patches --damage-patches 8 `
    --damages "0.10,0.20,0.25,0.30,0.40,0.50,0.60" `
    --seeds $Seeds `
    --out $curveOut

Write-Host "=== answer field vs repair ===" -ForegroundColor Cyan
python tools/bench_exp_j_repair_answer.py `
    --queries lab/exp_j_ru_queries.jsonl `
    --store-dir $store --model $model `
    --out "lab/exp_j_ru_v1/report_repair_${tag}.json"

Write-Host "Done. model=$model curve=$curveOut"
