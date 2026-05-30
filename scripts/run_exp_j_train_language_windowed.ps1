# Exp J phase D: windowed NCA on LANGUAGE only (grammar + literacy, no MRE3).
param(
    [int]$Epochs = 600,
    [int]$Seeds = 20,
    [switch]$SkipCurve
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$store = 'lab/agent-stores/language-agent-lab-v0'
$grammar = "$store/bundles/kb-russian-language-rules-v1.bundle.v1.json"
$literacy = "$store/bundles/kb-russian-literacy-agent.bundle.v1.json"
$bundles = @($grammar, $literacy)
$outDir = 'lab/nca_out_exp_j_ru_language_windowed_v1'
$reportDir = 'lab/exp_j_ru_v1'

if (-not (Test-Path $literacy)) {
    throw "Run run_exp_j0_literacy_sync.ps1 first (missing $literacy)"
}

Write-Host "=== Exp J LANGUAGE windowed train epochs=$Epochs ===" -ForegroundColor Cyan
$env:PYTHONUNBUFFERED = '1'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
python tools/train_dmn_nca_windowed.py `
    --bundles $bundles `
    --codec v3 --concept-mode section `
    --tile-w 32 --tile-h 32 --stride-x 16 --stride-y 16 --ghost 2 `
    --windows-per-batch 0 `
    --damage-mode patches --damage-patches 6 `
    --epochs $Epochs --save-model `
    --out-dir $outDir

$model = "$outDir/model.pt"
if (-not (Test-Path $model)) { throw "No model at $model" }
$sw.Stop()
Write-Host ("Train: {0:N1}s ({1:N2} min)" -f $sw.Elapsed.TotalSeconds, ($sw.Elapsed.TotalSeconds / 60)) -ForegroundColor DarkGray

$ckpt = "$store/checkpoints/model_hard.pt"
New-Item -ItemType Directory -Force -Path "$store/checkpoints" | Out-Null
Copy-Item -Force $model $ckpt
Write-Host "Checkpoint: $ckpt"

Write-Host '=== windowed repair (grammar bundle probe) ===' -ForegroundColor Cyan
python tools/bench_windowed_repair.py `
    --bundle $grammar `
    --model $model `
    --codec v3 --concept-mode section `
    --out "$reportDir/report_language_windowed_repair.json"

if (-not $SkipCurve -and $Epochs -ge 200) {
    $curveOut = "$reportDir/curve_language_windowed_s${Seeds}.json"
    python tools/bench_curve_dmn_nca_union.py `
        --bundle $grammar `
        --model $model `
        --codec v3 --concept-mode section `
        --damage-mode patches --damage-patches 8 `
        --damages "0.10,0.20,0.25,0.30,0.40,0.50,0.60" `
        --seeds $Seeds `
        --out $curveOut
}

Write-Host "Done. model=$model"
