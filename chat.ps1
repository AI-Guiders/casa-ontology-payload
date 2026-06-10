#!/usr/bin/env pwsh
# One-click: life reactor (if needed) + console chat.
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

$StoreDir = if ([System.IO.Path]::IsPathRooted($Store)) {
    $Store
} else {
    Join-Path $Root ('agents\' + $Store)
}

$ensure = @"
from pathlib import Path
from casa.cli.life_daemon import ensure_life_reactor
import sys
sys.exit(0 if ensure_life_reactor(Path(r'$StoreDir')) else 1)
"@
& $Py -c $ensure
if ($LASTEXITCODE -ne 0) {
    Write-Host '[chat] Не удалось поднять life reactor.' -ForegroundColor Red
    exit 1
}

& $Py -m casa.cli chat --store $Store --no-daemon @ChatArg
exit $LASTEXITCODE
