# SN/CEN field hot path + import finetune smoke
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== Hot path from field_state ==="
python tools/sn_cen_infer.py --from-field --query "import knowledge delta" `
  --out lab/sn_cen_out/from_field_v1.json

Write-Host "`n=== Patch import with auto finetune (120 epochs) ==="
python tools/import_knowledge_delta.py `
  --delta lab/test-deltas/patch-import-concept.v0.json `
  --finetune-epochs 80 --bench

Write-Host "`n=== Hot path again after finetune ==="
python tools/sn_cen_infer.py --from-field --query "import knowledge delta" `
  --out lab/sn_cen_out/from_field_after_ft_v1.json

Write-Host "Done."
