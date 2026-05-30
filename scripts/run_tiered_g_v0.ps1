# Experiment G: tiered train (easy=cluster only, hard=cluster+module finetune)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUNBUFFERED = 1
Write-Host "=== Experiment G: tiered train + bench ===" -ForegroundColor Cyan
python tools/exp_g_tiered.py --phase1-epochs 600 --phase2-epochs 200 --seeds 15

Write-Host "=== Compare G vs E ===" -ForegroundColor Cyan
python -c "
import json
from pathlib import Path
e = json.loads(Path('examples/exp_e_clusters_v1/report.json').read_text(encoding='utf-8'))
g = json.loads(Path('examples/exp_g_tiered_v1/report.json').read_text(encoding='utf-8'))
for ge, gg in zip(e['clusters'], g['clusters']):
    print(f\"{ge['cluster']}: E d_mix={ge['mean_delta_mix']:.4f} ({ge['nca_wins']} wins) | G d_mix={gg['mean_delta_mix']:.4f} ({gg['nca_wins']} wins)\")
"

Write-Host "Done."
