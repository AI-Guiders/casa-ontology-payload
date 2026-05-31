# BiT9 track A gate — linked RU (modern) + EN, no NCA wait.
# Run from casa-ontology-payload/: .\scripts\run_bit9_gate.ps1
#
# Phases:
#   1) smoke — merged_preview eval (6/6 canonical) + integration benches
#   2) scale — T9 sweep on --Sample words per store (default 1000); use -SmokeOnly to skip
#
# With --out, benches print only SUMMARY (stderr), not multi-MB JSON to the terminal.

param(
    [int]$Sample = 1000,
    [int]$Seed = 42,
    [switch]$SmokeOnly
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

$RuStore = "lab/agent-stores/sss-ru-general"
$EnStore = "lab/agent-stores/sss-en-folk"
$ReportDir = "lab/exp_bilingual/reports"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

function Invoke-Bench {
    param(
        [string]$Name,
        [Parameter(Mandatory)]
        [string[]]$PythonArgv
    )
    if ($PythonArgv.Count -lt 1 -or $PythonArgv[0] -notmatch '\.py$') {
        throw "Invoke-Bench $Name : bad PythonArgv (first must be tools/*.py)"
    }
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    Write-Host "  python $($PythonArgv -join ' ')" -ForegroundColor DarkGray
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & python @PythonArgv
    if (-not $?) { $code = 1 } else { $code = $LASTEXITCODE }
    $sw.Stop()
    if ($code -ne 0) {
        throw "$Name failed (exit $code) after $($sw.Elapsed.TotalSeconds.ToString('0.0'))s"
    }
    Write-Host "  done $($sw.Elapsed.TotalSeconds.ToString('0.0'))s" -ForegroundColor DarkGray
}

Write-Host "BiT9 gate — smoke (integration cues)" -ForegroundColor Yellow

Invoke-Bench -Name "bench_bit9_merged_preview" -PythonArgv @(
    "tools/bench_bit9_merged_preview.py",
    "--ru-store", $RuStore,
    "--en-store", $EnStore,
    "--out", "$ReportDir/bit9_merged_preview.json"
)

Invoke-Bench -Name "bench_bilingual_linked" -PythonArgv @(
    "tools/bench_bilingual_linked.py",
    "--ru-store", $RuStore,
    "--en-store", $EnStore,
    "--out", "$ReportDir/bit9_linked_ru_general.json"
)

Invoke-Bench -Name "bench_unified_tick" -PythonArgv @(
    "tools/bench_unified_tick.py",
    "--ru-store", $RuStore,
    "--en-store", $EnStore,
    "--out", "$ReportDir/bit9_unified_tick.json"
)

Invoke-Bench -Name "bench_ambiguous_prefix" -PythonArgv @(
    "tools/bench_ambiguous_prefix.py",
    "--ru-store", $RuStore,
    "--en-store", $EnStore,
    "--out", "$ReportDir/bit9_ambiguous_prefix.json"
)

Invoke-Bench -Name "t9_runtime_once" -PythonArgv @(
    "tools/t9_runtime.py", "once", "--prefix", "co",
    "--summary", "--out", "$ReportDir/bit9_runtime_co.json"
)

if (-not $SmokeOnly) {
    Write-Host "`nBiT9 gate — scale (T9 sweep $Sample words/store, policy=lab, full>=99%%, prefix>=15%%)" -ForegroundColor Yellow

    Invoke-Bench -Name "ru_t9_sweep_${Sample}" -PythonArgv @(
        "tools/bench_t9_lexicon_sweep.py",
        "--store-dir", $RuStore,
        "--sample", "$Sample",
        "--seed", "$Seed",
        "--t9-policy", "lab",
        "--min-full-rate", "0.99",
        "--min-prefix-rate", "0.15",
        "--out", "$ReportDir/bit9_ru_sweep_${Sample}.json"
    )

    Invoke-Bench -Name "en_t9_sweep_${Sample}" -PythonArgv @(
        "tools/bench_t9_lexicon_sweep.py",
        "--store-dir", $EnStore,
        "--sample", "$Sample",
        "--seed", "$Seed",
        "--t9-policy", "lab",
        "--min-full-rate", "0.99",
        "--min-prefix-rate", "0.15",
        "--out", "$ReportDir/bit9_en_sweep_${Sample}.json"
    )
}

Write-Host "`nBiT9 gate: all passed. Reports -> $ReportDir" -ForegroundColor Green
