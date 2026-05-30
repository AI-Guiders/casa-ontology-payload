# Experiment J: answer recall + optional repair bench.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$store = 'examples/agent-stores/language-agent-lab-v0'
$model = 'examples/nca_out_exp_j_ru_v1/model.pt'
if (-not (Test-Path $model)) { $model = "$store/checkpoints/model_hard.pt" }

python tools/bench_answer_recall.py `
  --queries examples/exp_j_ru_queries.jsonl `
  --store-dir $store `
  --out examples/exp_j_ru_v1/report.json

if (Test-Path $model) {
  python tools/bench_exp_j_repair_answer.py `
    --queries examples/exp_j_ru_queries.jsonl `
    --store-dir $store --model $model `
    --out examples/exp_j_ru_v1/report_repair.json
}
