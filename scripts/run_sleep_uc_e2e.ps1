# Sleep UC end-to-end: Use -> Extract -> Remember (--write) -> reload -> Use
# Run from casa-ontology-payload/: .\scripts\run_sleep_uc_e2e.ps1

param(
    [string]$StoreDir = "lab/agent-stores/lexicon-ru-general",
    [switch]$NoWrite,
    [switch]$NoBackup
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

$ReportDir = "lab/exp_sleep/reports"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

$argv = @(
    "tools/run_sleep_uc_e2e.py",
    "--store-dir", $StoreDir,
    "--out", "$ReportDir/sleep_uc_e2e_v1.json"
)
if (-not $NoWrite) { $argv += "--write" }
if (-not $NoBackup) { $argv += "--backup" }

Write-Host "Sleep UC e2e on $StoreDir" -ForegroundColor Yellow
Write-Host "  python $($argv -join ' ')" -ForegroundColor DarkGray
& python @argv
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "`nSleep UC e2e: passed. Report -> $ReportDir/sleep_uc_e2e_v1.json" -ForegroundColor Green
