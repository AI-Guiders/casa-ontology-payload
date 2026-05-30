# KB watcher for modern RU language store.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$env:AGENT_NOTES_KB = 'D:\experiments\agent-notes\knowledge'
$store = 'examples/agent-stores/language-agent-lab-v0'
$manifest = 'manifests/kb-bundles-russian-language.json'

if ($args -contains '--once') {
  python tools/kb_field_watcher.py --store-dir $store --manifest $manifest --once
} else {
  python tools/kb_field_watcher.py --store-dir $store --manifest $manifest @args
}
