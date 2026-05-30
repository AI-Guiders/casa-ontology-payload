# Afan-III: wake episodes → sleep → NCA train/repair on L1 (L2 too large for NCA)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$srcStore = 'examples/agent-stores/sss-afan-v0'
$store = 'examples/agent-stores/sss-afan-iii-v0'
$bukvar = 'examples/kb/kb-bukvar-ru-full-v1.payload.json'
$exp = 'examples/exp_sss_v1'
$ncaOut = 'examples/nca_out_afan_l1_v0'
$lattice = 'L1_syllable'

Write-Host '=== Afan-III: copy golden store (once) ===' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $store | Out-Null
$dst = Join-Path $store 'field_state.json'
if (-not (Test-Path $dst)) {
    Copy-Item (Join-Path $srcStore 'field_state.json') $dst
    Write-Host "Copied field_state to $store"
} else {
    Write-Host "Using existing $dst"
}

Write-Host '=== wake: record episodes (volk, kolobok, pa) ===' -ForegroundColor Cyan
python tools/sss_wake_batch_v0.py `
    --store-dir $store `
    --episodes "$exp/afan_wake_episodes.json" `
    --bundle $bukvar `
    | Tee-Object -FilePath "$exp/report_afan_iii_wake.json"

Write-Host '=== sleep bench BEFORE (volk votes) ===' -ForegroundColor Cyan
python tools/bench_sss_sleep.py `
    --store-dir $store `
    --bundle $bukvar `
    --target "$exp/afan_sleep_target_volk.json" `
    | Tee-Object -FilePath "$exp/report_afan_iii_sleep_before.json"

Write-Host '=== T_sleep: consolidate hippo → memory ===' -ForegroundColor Cyan
python tools/sss_sleep_v0.py `
    --store-dir $store `
    --bundle $bukvar `
    | Tee-Object -FilePath "$exp/report_afan_iii_sleep_run.json"

Write-Host '=== sleep bench AFTER ===' -ForegroundColor Cyan
python tools/bench_sss_sleep.py `
    --store-dir $store `
    --bundle $bukvar `
    --target "$exp/afan_sleep_target_volk.json" `
    | Tee-Object -FilePath "$exp/report_afan_iii_sleep_after.json"

Write-Host "=== NCA train $lattice (~924 tokens, not full L2) ===" -ForegroundColor Cyan
python tools/train_sss_nca_v0.py `
    --store-dir $store `
    --lattice-id $lattice `
    --epochs 150 `
    --device cuda `
    --out-dir $ncaOut `
    --save-model

Write-Host '=== NCA damage → repair bench (no write to store) ===' -ForegroundColor Cyan
python tools/bench_sss_nca_repair.py `
    --store-dir $store `
    --lattice-id $lattice `
    --model "$ncaOut/model.pt" `
    --out "$exp/report_afan_iii_nca_repair.json"

Write-Host '=== sleep + NCA regrow on L1 ===' -ForegroundColor Cyan
python tools/sss_sleep_nca_hook_v0.py `
    --store-dir $store `
    --model "$ncaOut/model.pt" `
    --lattice-id $lattice `
    --bukvar $bukvar `
    --text examples/text/kolobok-excerpt.txt `
    | Tee-Object -FilePath "$exp/report_afan_iii_sleep_nca.json"

Write-Host '=== babble spot-check after sleep ===' -ForegroundColor Cyan
python tools/sss_babble_v0.py --store-dir $store --lattice L2_word --prompt-file "$exp/afan_cue_volk.txt"

Write-Host 'Done. Working store:' $store '(golden' $srcStore 'untouched)'
