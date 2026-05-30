# Substrate v2 smoke — ingest, union field, from-field SN/CEN
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$store = "examples/agent-stores/research-agent-lab-v0"
$bundle = "examples/kb-perdoc/research-ml.bundle.v1.json"

Write-Host "== import (union field) =="
python tools/import_knowledge_delta.py `
  --delta examples/agent-cards/sample-knowledge-delta.v0.json `
  --store-dir $store 2>$null
if ($LASTEXITCODE -ne 0) {
  python tools/import_knowledge_delta.py `
    --delta examples/test-deltas/patch-import-concept.v0.json `
    --store-dir $store
}

Write-Host "== digest_only =="
python tools/import_knowledge_delta.py `
  --delta examples/test-deltas/digest-only-research-ml.v0.json `
  --store-dir $store

Write-Host "== from-field SN/CEN v2 =="
python tools/sn_cen_infer.py --from-field --query "import knowledge delta" `
  --out examples/sn_cen_out/_substrate_v2_smoke.json

Write-Host "OK: examples/sn_cen_out/_substrate_v2_smoke.json"
