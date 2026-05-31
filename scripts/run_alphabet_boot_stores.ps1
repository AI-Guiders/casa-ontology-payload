# Merge alphabet into stores with empty L0; optional VK NCA on core.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUTF8 = '1'

Write-Host '=== Alphabet into empty-L0 stores ===' -ForegroundColor Green
python tools/boot_alphabet_into_stores.py --compact

Write-Host '=== VK core NCA (cuda) ===' -ForegroundColor Cyan
python tools/vk_nca_train.py --device cuda

Write-Host 'Done.' -ForegroundColor Green
