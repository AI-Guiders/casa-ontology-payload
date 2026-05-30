# Afan-II: babble + held-out (field only, claims_nav ablated)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-afan-v0'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$outDir = 'lab/exp_sss_v1'

Write-Host '=== Afan-II: held-out surface (mixed cases) ===' -ForegroundColor Cyan
python tools/bench_sss_heldout.py `
    --store-dir $store `
    --bundle $bundle `
    --cases "$outDir/heldout_afan_v0.json" `
    --top-k 3 `
    --out "$outDir/report_afan_heldout.json"

Write-Host '=== Afan-II: bukvar syllables only (smoke baseline) ===' -ForegroundColor Cyan
python tools/bench_sss_heldout.py `
    --store-dir $store `
    --bundle $bundle `
    --cases "$outDir/heldout_syllables.json" `
    --top-k 3 `
    --out "$outDir/report_afan_heldout_bukvar.json"

Write-Host '=== Afan-II: sample surface surfaces ===' -ForegroundColor Cyan
python tools/sss_surface_v0.py --store-dir $store --lattice L1_syllable --prompt "п а"
python tools/sss_surface_v0.py --store-dir $store --lattice L1_syllable --prompt "г о"
python tools/sss_surface_v0.py --store-dir $store --lattice L2_word --prompt "колобок"

Write-Host 'Done. Reports:' "$outDir/report_afan_heldout.json"
