# Latency bench smoke
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

python tools/bench_latency_qwen_casa.py --skip-qwen
Write-Host "CASA latency done (Qwen skipped if offline). Run without --skip-qwen when Ollama is up."
