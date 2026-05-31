# Import knowledge delta smoke
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

python tools/import_knowledge_delta.py `
  --delta lab/agent-cards/sample-knowledge-delta.json `
  --copy-checkpoint --bench

python tools/import_knowledge_delta.py `
  --delta lab/test-deltas/patch-import-concept.json `
  --bench

Write-Host "Import delta smoke done. See lab/agent-stores/research-agent-lab/"
