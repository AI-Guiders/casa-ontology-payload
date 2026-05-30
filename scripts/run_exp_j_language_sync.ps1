# Experiment J: sync modern Russian KB bundles (no pre-revolutionary orthography).
$ErrorActionPreference = 'Stop'
$env:AGENT_NOTES_KB = 'D:\experiments\agent-notes\knowledge'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$manifest = 'manifests/kb-bundles-russian-language.json'
$store = 'lab/agent-stores/language-agent-lab-v0'
$card = 'lab/agent-cards/research-agent.v0.json'

$docs = @(
    'kb-russian-language-rules-v1',
    'kb-regex-mre3-ru-chapter-map-v1'
)

# Drop legacy bundle from store (дореформенная орфография).
$legacy = Join-Path $store 'bundles/pre-revolutionary-russian-orthography-v1.bundle.v1.json'
if (Test-Path $legacy) {
    Remove-Item -Force $legacy
    Write-Host "Removed legacy bundle: $legacy"
}

foreach ($doc in $docs) {
    Write-Host "=== sync $doc ==="
    python tools/kb_sync.py `
        --manifest $manifest `
        --doc $doc `
        --import-to $store `
        --agent-card $card `
        --tier easy
}

Write-Host "=== rebuild union field ==="
python tools/rebuild_agent_store.py --store-dir $store

Write-Host "Done. field_state: $store/field_state.json"
