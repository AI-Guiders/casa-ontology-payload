# L2 shard network smoke + dry-run NCA shard train plan
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-shard-smoke'
$bukvar = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$exp = 'lab/exp_sss_v1'

Write-Host '=== init small store ===' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $store | Out-Null
python tools/gen_kb_bukvar_ru_full.py --out $bukvar
python tools/sss_field.py --store-dir $store --bundle $bukvar --listen-passes 2 --init

Write-Host '=== ingest kolobok (words -> shards) ===' -ForegroundColor Cyan
python tools/sss_text_listen_field.py --store-dir $store --text lab/text/kolobok-excerpt.txt --bukvar $bukvar

Write-Host '=== shard stats + babble ===' -ForegroundColor Cyan
python tools/bench_sss_l2_shard.py --store-dir $store --write `
    | Tee-Object -FilePath "$exp/report_l2_shard_smoke.json"

Write-Host '=== NCA train plan (dry-run) ===' -ForegroundColor Cyan
python tools/train_sss_nca_shards.py --store-dir $store --layer L2 --dry-run `
    | Tee-Object -FilePath "$exp/report_l2_shard_nca_plan.json"

Write-Host '=== Afan stats (legacy monolith, read-only) ===' -ForegroundColor Cyan
python -c "import json,sys; sys.path.insert(0,'tools'); from pathlib import Path; from field_write import load_field_state; from sss_cylinders import ensure_cylinders; from sss_l2_shard import shard_stats; s=ensure_cylinders(load_field_state(Path('lab/agent-stores/sss-afan/field_state.json'))); print(json.dumps(shard_stats(s), ensure_ascii=False, indent=2))" `
    | Tee-Object -FilePath "$exp/report_afan_l2_shard_stats.json"

Write-Host 'Done.'
