# One-shot lab store migration (math-l0-lab, journal → language-agent-lab, clean sss-ru-general)
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m casa.cli migrate_agent_lab_stores @args
