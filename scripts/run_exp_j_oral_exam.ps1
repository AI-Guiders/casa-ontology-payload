# Exp J oral exam: off-topic guard + grammar + paraphrase + curated oral set.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = 'utf-8'
. (Join-Path $PSScriptRoot '_kb_env.ps1')
Require-AgentNotesKb

$store = 'lab/agent-stores/language-agent-lab-v0'
$out = 'lab/exp_j_ru_v1'

python tools/bench_off_topic_guard.py --queries "$out/queries_off_topic.jsonl" --store-dir $store --out "$out/report_off_topic_guard.json"
python tools/bench_oral_exam.py --queries "$out/queries_oral_exam.jsonl" --store-dir $store --out "$out/report_oral_exam.json"
python tools/bench_answer_recall.py --queries "$out/queries_grammar.jsonl" --store-dir $store --out "$out/report_grammar_recall_oral.json"
python tools/bench_write_sketch.py --queries "$out/queries_grammar.jsonl" --store-dir $store --out "$out/report_write_grammar_oral.json"
python tools/bench_answer_recall.py --queries lab/exp_j0_literacy/queries_paraphrase.jsonl --store-dir $store --out "$out/report_paraphrase_oral.json"
python tools/bench_write_sketch.py --queries lab/exp_j0_literacy/queries_write.jsonl --store-dir $store --out "$out/report_write_oral.json"

Write-Host "Done. See $out/report_*_oral.json and report_oral_exam.json"
