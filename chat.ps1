#!/usr/bin/env pwsh
# One-click console chat (life reactor auto-start inside chat).
#   .\chat.ps1
#   .\chat.ps1 --verbose --store von-neumann

#Requires -Version 5.1

param(
    [string] $Store = 'von-neumann',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ChatArg
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

$Root = $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Py)) {
    Write-Host '[chat] .venv not found. Create it first:' -ForegroundColor Yellow
    Write-Host '    py -3.12 -m venv .venv'
    Write-Host '    .\.venv\Scripts\python -m pip install -r tools\requirements.txt'
    exit 1
}

& $Py -m casa.cli chat --store $Store @ChatArg
exit $LASTEXITCODE
