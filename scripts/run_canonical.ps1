# Canonical v3/section union train + curve on primary bundle (local lab).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$bundles = @(
  "lab/ca-substrate-agent.bundle.v1.json",
  "lab/casa-goals.bundle.v1.json",
  "lab/research-spec.bundle.v1.json"
)

python -m pip install -q -r tools/requirements.txt

python tools/train_dmn_nca_multibundle.py `
  --bundles @bundles `
  --codec v3 --concept-mode section `
  --epochs 900 --save-model `
  --out-dir lab/nca_out_canonical_v3_section

$model = "lab/nca_out_canonical_v3_section/model.pt"
foreach ($b in $bundles) {
  $stem = [System.IO.Path]::GetFileNameWithoutExtension($b)
  python tools/bench_curve_dmn_nca_union.py `
    --bundle $b --model $model `
    --codec v3 --concept-mode section `
    --seeds 20 `
    --out "lab/nca_v3_section_curve_${stem}_s20.json"
}

Write-Host "Done. Model: $model"
