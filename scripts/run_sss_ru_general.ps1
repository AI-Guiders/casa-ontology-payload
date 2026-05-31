# Modern RU lexicon (DetCorpus) — not Afan. Usage axes + optional NCA.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

$store = 'lab/agent-stores/sss-ru-general'
$exp = 'lab/exp_t9'

Write-Host '=== 0) DetCorpus headwords + usage axes ===' -ForegroundColor Green
python tools/fetch_ru_frequency_headwords.py
python tools/build_lexicon_usage_axes.py --corpus ru-general

Write-Host '=== 1) Init store (L0+L2+ltm+axes) ===' -ForegroundColor Green
python tools/init_lexicon_store.py --corpus-id ru-general
if ($LASTEXITCODE -ne 0) { throw "init_lexicon_store failed" }

Write-Host '=== 2) NCA train (CUDA) ===' -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $exp | Out-Null
python tools/train_sss_nca_shards.py `
    --store-dir $store `
    --layer all `
    --device cuda `
    2>&1 | Tee-Object -FilePath "$exp/nca_train_ru_general_cuda.log"
if ($LASTEXITCODE -ne 0) { throw "train_sss_nca_shards (cuda) failed" }

Write-Host '=== 3) T9 sweep (prod policy = active+rare modern) ===' -ForegroundColor Green
python tools/bench_t9_lexicon_sweep.py `
    --store-dir $store `
    --prefer-field-state `
    --t9-policy prod `
    --out "$exp/report_sweep_ru_general_prod.json"

Write-Host "Done. Profile: lab/agent-profiles/bilingual-t9-console.json -> $store"
