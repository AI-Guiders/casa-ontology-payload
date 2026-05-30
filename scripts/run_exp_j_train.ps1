# Experiment J phase 2: train union NCA on modern RU store bundles + bench.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'lab/agent-stores/language-agent-lab-v0'
$outDir = 'lab/nca_out_exp_j_ru_v1'
$bundles = @(
  "$store/bundles/kb-russian-language-rules-v1.bundle.v1.json",
  "$store/bundles/kb-regex-mre3-ru-chapter-map-v1.bundle.v1.json"
)

Write-Host '=== train union (RU modern) ===' -ForegroundColor Cyan
python tools/train_dmn_nca_multibundle.py `
  --bundles @bundles `
  --codec v3 --concept-mode section `
  --damage-mode patches --damage-patches 8 `
  --epochs 600 --save-model `
  --out-dir $outDir

$model = "$outDir/model.pt"
$ckptDir = "$store/checkpoints"
New-Item -ItemType Directory -Force -Path $ckptDir | Out-Null
Copy-Item -Force $model "$ckptDir/model_hard.pt"
Write-Host "Checkpoint: $ckptDir/model_hard.pt"

Write-Host '=== bench F1 (grammar bundle, damage 0.25) ===' -ForegroundColor Cyan
python tools/bench_dmn_nca_union.py `
  --bundle "$store/bundles/kb-russian-language-rules-v1.bundle.v1.json" `
  --model $model --codec v3 --concept-mode section `
  --damage-mode patches --damage-patches 8 --seeds 12 `
  --out lab/exp_j_ru_v1/nca_bench_grammar_s12.json

Write-Host '=== bench answer: field vs repair ===' -ForegroundColor Cyan
python tools/bench_exp_j_repair_answer.py `
  --queries lab/exp_j_ru_queries.jsonl `
  --store-dir $store --model $model `
  --out lab/exp_j_ru_v1/report_repair.json

Write-Host 'Done.'
