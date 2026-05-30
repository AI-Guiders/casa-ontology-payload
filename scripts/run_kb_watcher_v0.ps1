# Watch KB markdown → kb_sync → field import (stdlib poll)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$store = "examples/agent-stores/research-agent-lab-v0"
if ($args -contains "--once") {
  python tools/kb_field_watcher.py --store-dir $store --once
} else {
  python tools/kb_field_watcher.py --store-dir $store @args
}
