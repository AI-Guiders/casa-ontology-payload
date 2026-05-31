# SSS damage → cross-lattice repair (brain-like plasticity)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-full'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'

Write-Host '=== ensure full alphabet store ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle
python tools/sss_field.py --store-dir $store --bundle $bundle --listen-passes 4 --init

Write-Host '=== damage L0 (alphabet patch holes) ===' -ForegroundColor Cyan
python tools/bench_sss_damage_repair.py `
    --store-dir $store `
    --bundle $bundle `
    --damage-lattice L0_grapheme `
    --damage-patches 8 `
    --seed 42 `
    --out lab/exp_sss_v1/report_damage_l0_field.json

Write-Host '=== repair: field plasticity + optional canonical gaps ===' -ForegroundColor Cyan
python tools/bench_sss_damage_repair.py `
    --store-dir $store `
    --bundle $bundle `
    --damage-lattice L0_grapheme `
    --damage-patches 8 `
    --seed 42 `
    --allow-canonical `
    --write `
    --out lab/exp_sss_v1/report_damage_l0_repaired.json

Write-Host '=== damage L1, repair via L0+L2 ===' -ForegroundColor Cyan
python tools/bench_sss_damage_repair.py `
    --store-dir $store `
    --bundle $bundle `
    --damage-lattice L1_syllable `
    --damage-patches 6 `
    --seed 7 `
    --allow-canonical `
    --out lab/exp_sss_v1/report_damage_l1_repaired.json

Write-Host 'Done.'
