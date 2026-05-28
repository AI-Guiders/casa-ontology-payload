# Layered piston v0: DMN checkpoint + optional digest train + infer
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$bundle = "examples/ca-substrate-agent.bundle.v1.json"
$dmn = "examples/nca_out_v3_section/model.pt"
if (-not (Test-Path $dmn)) { $dmn = "examples/exp_d_kb_perdoc_v1/model.pt" }

python -m pip install -q -r tools/requirements.txt

Write-Host "=== Train digest layer (z=2) ===" -ForegroundColor Cyan
python tools/train_layer_digest.py --bundle $bundle --dmn-model $dmn --epochs 300 --out examples/layered_out/digest_model.pt

Write-Host "=== Layered infer (piston) ===" -ForegroundColor Cyan
python tools/layered_infer.py --bundle $bundle --dmn-model $dmn --digest-model examples/layered_out/digest_model.pt
