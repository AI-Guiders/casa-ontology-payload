# SN + CEN smoke (v1)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

python tools/sn_cen_infer.py `
  --bundle examples/kb-perdoc/research-ml.bundle.v1.json `
  --out examples/sn_cen_out/research-ml_v1.json

python tools/sn_cen_infer.py `
  --bundle examples/kb-perdoc/research-tda-flow.bundle.v1.json `
  --query "topological data analysis" `
  --out examples/sn_cen_out/research-tda-flow_query_v1.json

Write-Host "SN+CEN smoke done."
