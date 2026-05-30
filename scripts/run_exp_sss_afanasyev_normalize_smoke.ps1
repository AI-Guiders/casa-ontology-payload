# Download Afanasyev from lib.ru → per-tale corpus (smoke: 30 tales vol 1)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

Write-Host '=== normalize Afanasyev vol.1 (first 30 tales) ===' -ForegroundColor Cyan
python tools/normalize_afanasyev_txt_v0.py `
    --download-libru `
    --volumes 1 `
    --limit 30 `
    --out-dir examples/text/corpus/afanasyev `
    --manifest examples/exp_sss_v1/report_afanasyev_normalize_smoke.json

Write-Host '=== sample file ===' -ForegroundColor Cyan
Get-Content examples/text/corpus/afanasyev/afan-v1-n001.txt -Encoding UTF8 -TotalCount 12

Write-Host 'Done.'
