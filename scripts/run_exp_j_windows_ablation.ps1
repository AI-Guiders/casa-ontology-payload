# Union vocab (162): ablation windows_per_batch 1 vs 32 vs 48, optional stride 8.
param(
    [int]$Epochs = 400,
    [switch]$SkipW48,
    [switch]$SkipS8
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUNBUFFERED = '1'

$bundles = @(
    'examples/agent-stores/language-agent-lab-v0/bundles/kb-russian-language-rules-v1.bundle.v1.json',
    'examples/agent-stores/language-agent-lab-v0/bundles/kb-regex-mre3-ru-chapter-map-v1.bundle.v1.json'
)
$reportDir = 'examples/exp_j_ru_v1'
$rows = @()

function Invoke-Arm {
    param(
        [string]$Arm,
        [int]$WinBatch,
        [int]$Stride,
        [string]$OutDir
    )
    Write-Host "=== arm $Arm windows_per_batch=$WinBatch stride=$Stride epochs=$Epochs ===" -ForegroundColor Cyan
    $sw = [Diagnostics.Stopwatch]::StartNew()
    python tools/train_dmn_nca_windowed.py `
        --bundles $bundles `
        --codec v3 --concept-mode section `
        --tile-w 32 --tile-h 32 `
        --stride-x $Stride --stride-y $Stride --ghost 2 `
        --windows-per-batch $WinBatch `
        --max-windows-per-batch 64 `
        --damage-mode patches --damage-patches 6 `
        --epochs $Epochs --save-model `
        --out-dir $OutDir
    $sw.Stop()
    $rep = Get-Content "$OutDir/report.json" -Raw | ConvertFrom-Json
    $model = "$OutDir/model.pt"
    python tools/bench_windowed_repair.py `
        --bundle $bundles[0] `
        --model $model `
        --codec v3 --concept-mode section `
        --tile-w 32 --tile-h 32 --stride-x $Stride --stride-y $Stride --ghost 2 `
        --out "$reportDir/report_ablation_${Arm}_repair.json"
    $bench = Get-Content "$reportDir/report_ablation_${Arm}_repair.json" -Raw | ConvertFrom-Json
    return [PSCustomObject]@{
        arm              = $Arm
        windows_per_batch = $WinBatch
        stride           = $Stride
        epochs           = $Epochs
        tile_count       = $rep.planner.tile_count
        windows_seen     = $Epochs * $WinBatch
        train_wall_sec   = $rep.train_wall_sec
        sec_per_epoch    = [math]::Round($rep.train_wall_sec / $Epochs, 3)
        best_mix         = $rep.best_mix
        repair_mix       = $bench.mix_windowed
        concepts_f1      = $bench.windowed.concepts.f1
        out_dir          = $OutDir
    }
}

$rows += Invoke-Arm -Arm 'w1' -WinBatch 1 -Stride 16 -OutDir 'examples/nca_out_exp_j_ablation_w1_v1'
$rows += Invoke-Arm -Arm 'w32' -WinBatch 32 -Stride 16 -OutDir 'examples/nca_out_exp_j_ablation_w32_v1'
if (-not $SkipW48) {
    $rows += Invoke-Arm -Arm 'w48' -WinBatch 48 -Stride 16 -OutDir 'examples/nca_out_exp_j_ablation_w48_v1'
}
if (-not $SkipS8) {
    $rows += Invoke-Arm -Arm 'w32_s8' -WinBatch 32 -Stride 8 -OutDir 'examples/nca_out_exp_j_ablation_w32_s8_v1'
}

$outPath = "$reportDir/windows_ablation_report.json"
@{
    schema_version = 1
    note           = 'Union vocab 162. windows_seen = epochs * windows_per_batch.'
    rows           = @($rows)
} | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding utf8
Write-Host ''
Write-Host $outPath -ForegroundColor Green
$rows | Format-Table arm, windows_per_batch, stride, tile_count, windows_seen, train_wall_sec, sec_per_epoch, best_mix, repair_mix -AutoSize
