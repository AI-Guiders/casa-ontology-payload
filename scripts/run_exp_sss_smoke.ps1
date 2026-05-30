# Exp SSS: lattice stack (z_level), listen, z_compose, babble from cylinder.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'lab/agent-stores/sss-lab-v0'
$bundle = 'lab/kb/kb-bukvar-ru-primer-v1.payload.json'
$stack = 'design/sss-lattice-stack.v0.json'

Write-Host '=== SSS: lattice stack + listen ===' -ForegroundColor Cyan
python tools/sss_field.py --store-dir $store --bundle $bundle --stack $stack --listen-passes 6 --init

Write-Host '=== SSS: lattice coverage + z_compose ===' -ForegroundColor Cyan
python tools/bench_sss_lattice.py `
    --store-dir $store `
    --bundle $bundle `
    --stack $stack `
    --out lab/exp_sss_v1/report_lattice.json

Write-Host '=== SSS: babble L0 L1 L2 ===' -ForegroundColor Cyan
python tools/sss_surface_v0.py --store-dir $store --lattice L0_grapheme --prompt 'м а'
python tools/sss_surface_v0.py --store-dir $store --lattice L1_syllable --prompt 'ма'
python tools/sss_surface_v0.py --store-dir $store --lattice L2_word --prompt 'мама'

Write-Host 'Done. Store:' $store
