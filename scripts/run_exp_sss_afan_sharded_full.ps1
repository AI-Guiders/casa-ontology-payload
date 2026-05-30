# Deprecated name — forwards to canonical ru-lexicon pipeline.
$ErrorActionPreference = 'Stop'
Write-Warning 'run_exp_sss_afan_sharded_full.ps1 is deprecated; use scripts/run_sss_ru_lexicon_v0.ps1'
& (Join-Path $PSScriptRoot 'run_sss_ru_lexicon_v0.ps1')
