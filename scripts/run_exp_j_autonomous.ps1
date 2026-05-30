# Experiment J: autonomous T-ticks with FPN session (demo).
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$store = 'examples/agent-stores/language-agent-lab-v0'
$goal = 'согласно приказу как правильно'

python tools/agent_autonomous_tick.py `
  --store-dir $store `
  --goal $goal `
  --ticks 3 `
  --out examples/exp_j_ru_v1/autonomous_ticks.json

Write-Host 'Session:' "$store/agent_session.json"
