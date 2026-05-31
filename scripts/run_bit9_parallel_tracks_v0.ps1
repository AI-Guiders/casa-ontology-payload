# BiT9 parallel tracks v0 — run A + C2 + prior benches concurrently.
# From casa-ontology-payload/: .\scripts\run_bit9_parallel_tracks_v0.ps1

param(
    [int]$Sample = 1000,
    [int]$Seed = 42,
    [int]$PosSample = 500,
    [switch]$SkipScale
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

$RuStore = "lab/agent-stores/sss-ru-general-v0"
$EnStore = "lab/agent-stores/sss-en-folk-v0"
$ReportDir = "lab/exp_bilingual_v0/reports"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

function Start-TrackJob {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "  start $Name" -ForegroundColor DarkGray
    Start-Job -Name $Name -ScriptBlock $Block
}

Write-Host "BiT9 parallel tracks — prep (UD POS maps + bundles)" -ForegroundColor Yellow

python tools/fetch_ud_lemma_pos_v0.py --locale ru
python tools/fetch_ud_lemma_pos_v0.py --locale en
python tools/build_pos_bundle_v0.py --locale ru --top-n 8000
python tools/build_pos_bundle_v0.py --locale en --top-n 8000

Write-Host "`nBiT9 parallel tracks — 4 jobs" -ForegroundColor Cyan

$root = (Get-Location).Path
$jobs = @(
    Start-TrackJob "track_a_merged" {
        Set-Location $using:root
        $env:PYTHONUTF8 = "1"
        python tools/bench_bit9_merged_preview_v0.py `
            --ru-store $using:RuStore --en-store $using:EnStore `
            --out "$using:ReportDir/bit9_merged_preview.json"
        exit $LASTEXITCODE
    }
    Start-TrackJob "track_a_scale_ru" {
        Set-Location $using:root
        $env:PYTHONUTF8 = "1"
        if (-not $using:SkipScale) {
            python tools/bench_t9_lexicon_sweep_v0.py `
                --store-dir $using:RuStore --sample $using:Sample --seed $using:Seed `
                --t9-policy lab --min-full-rate 0.99 --min-prefix-rate 0.15 `
                --out "$using:ReportDir/bit9_ru_sweep_$($using:Sample).json"
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        exit 0
    }
    Start-TrackJob "track_c2_pos" {
        Set-Location $using:root
        $env:PYTHONUTF8 = "1"
        python tools/bench_pos_claims_v0.py `
            --store-dir $using:RuStore `
            --bundle lab/kb/ru-pos-detcorpus-v1.json `
            --max-cues $using:PosSample `
            --out "$using:ReportDir/bit9_pos_detcorpus.json"
        exit $LASTEXITCODE
    }
    Start-TrackJob "track_c2_taxonomy_prior" {
        Set-Location $using:root
        $env:PYTHONUTF8 = "1"
        python tools/bench_entity_taxonomy_v0.py `
            --store-dir $using:RuStore `
            --out "$using:ReportDir/bit9_entity_taxonomy.json"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        python tools/bench_preview_semantic_prior_v0.py `
            --out "$using:ReportDir/bit9_semantic_prior.json"
        exit $LASTEXITCODE
    }
)

if (-not $SkipScale) {
    $jobs += Start-TrackJob "track_a_scale_en" {
        Set-Location $using:root
        $env:PYTHONUTF8 = "1"
        python tools/bench_t9_lexicon_sweep_v0.py `
            --store-dir $using:EnStore --sample $using:Sample --seed $using:Seed `
            --t9-policy lab --min-full-rate 0.99 --min-prefix-rate 0.15 `
            --out "$using:ReportDir/bit9_en_sweep_$($using:Sample).json"
        exit $LASTEXITCODE
    }
}

Write-Host "Waiting for $($jobs.Count) jobs …" -ForegroundColor DarkGray
$failed = @()
foreach ($j in ($jobs | Wait-Job)) {
    $out = Receive-Job -Job $j -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($j.State -eq "Failed") {
        $failed += $j.Name
    }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}

if ($failed.Count -gt 0) {
    throw "Failed tracks: $($failed -join ', ')"
}

Write-Host "`nBiT9 parallel tracks: all passed. Reports -> $ReportDir" -ForegroundColor Green
