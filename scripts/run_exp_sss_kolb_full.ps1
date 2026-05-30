# Full Kolb cycle: CE → RO → AC → sleep → AE (+ reload check)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$store = 'lab/agent-stores/sss-kolb-v0'
$bundle = 'lab/kb/kb-bukvar-ru-full-v1.payload.json'
$session = 'lab/exp_sss_v1/kolb_segment_session.json'
$report = 'lab/exp_sss_v1/report_kolb_full.json'

Write-Host '=== init (listen, no rules yet) ===' -ForegroundColor Cyan
python tools/gen_kb_bukvar_ru_full.py --out $bundle
python tools/sss_field.py --store-dir $store --bundle $bundle --listen-passes 2 --init

Write-Host '=== Kolb full cycle ===' -ForegroundColor Cyan
python tools/sss_kolb_cycle_v0.py `
    --store-dir $store `
    --session $session `
    --bundle $bundle `
    --out $report

Write-Host '=== bench Kolb ===' -ForegroundColor Cyan
python tools/bench_sss_kolb.py --report $report

Write-Host '=== reload store: AE on new word (persistence) ===' -ForegroundColor Cyan
python -c "import json; from pathlib import Path; import sys; sys.path.insert(0,'tools'); from field_write import load_field_state; from sss_hypothesis_v0 import hypothesis_turn; p=Path(r'$store/field_state.json'); w=Path('lab/exp_sss_v1/kolb_probe_klass.txt').read_text(encoding='utf-8').strip(); s=load_field_state(p); t=hypothesis_turn(s,w); print(json.dumps({'word':w,'attempt':t['attempt'],'inner_ok':t['verify']['ok'],'rule':t['hypothesis'].get('rule_id')}, ensure_ascii=False, indent=2))"

Write-Host '=== kolb history in field_state ===' -ForegroundColor Cyan
python -c "import json; from pathlib import Path; s=json.loads(Path(r'$store/field_state.json').read_text(encoding='utf-8')); print(json.dumps(s.get('kolb',{}), ensure_ascii=False, indent=2))"

Write-Host 'Done.'
