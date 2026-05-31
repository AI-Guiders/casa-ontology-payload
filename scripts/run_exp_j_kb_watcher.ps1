# KB watcher for modern RU language store.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_kb_env.ps1')
Require-AgentNotesKb
Set-Location (Split-Path -Parent $PSScriptRoot)

$store = 'lab/agent-stores/language-agent-lab-v0'
$manifest = 'manifests/kb-bundles-russian-language.json'

if ($args -contains '--once') {
  python tools/kb_field_watcher.py --store-dir $store --manifest $manifest --once
} else {
  python tools/kb_field_watcher.py --store-dir $store --manifest $manifest @args
}
