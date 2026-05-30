# Import knowledge delta smoke
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

python tools/import_knowledge_delta.py `
  --delta examples/agent-cards/sample-knowledge-delta.v0.json `
  --copy-checkpoint --bench

python tools/import_knowledge_delta.py `
  --delta examples/test-deltas/patch-import-concept.v0.json `
  --bench

Write-Host "Import delta smoke done. See examples/agent-stores/research-agent-lab-v0/"
