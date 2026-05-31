# Quad lexicon corpora: build headwords → imprint field → train NCA (CUDA) → manifest.
# After this, CASA only adds new words via lexicon_cold_ingest / sleep stale shards.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

$epochs = 25
if ($args -contains '--full-epochs') { $epochs = 80 }

Write-Host "=== 0a) RU general: frequency headwords (DetCorpus CC0) ===" -ForegroundColor Green
python tools/fetch_ru_frequency_headwords.py

Write-Host "=== 0) Build headword lists (Native AOT) ===" -ForegroundColor Green
$lexiconBuild = Join-Path $Root 'apps/Casa.Lexicon.Build/Casa.Lexicon.Build.csproj'
$publishDir = Join-Path $Root 'apps/Casa.Lexicon.Build/bin/Release/net10.0/win-x64/publish'
$exe = Join-Path $publishDir 'casa-lexicon-build.exe'
if (-not (Test-Path $exe)) {
    Write-Host 'Publishing casa-lexicon-build (win-x64, Native AOT)...' -ForegroundColor DarkGray
    dotnet publish $lexiconBuild -c Release -r win-x64 --no-restore 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        dotnet publish $lexiconBuild -c Release -r win-x64
        if ($LASTEXITCODE -ne 0) { throw 'dotnet publish casa-lexicon-build failed' }
    }
}
& $exe quad --root $Root
if ($LASTEXITCODE -ne 0) { throw 'casa-lexicon-build quad failed' }

$corpora = @('en-general', 'en-tech', 'ru-general', 'ru-tech')

foreach ($cid in $corpora) {
    Write-Host "=== Init + NCA: $cid ===" -ForegroundColor Cyan
    python tools/init_lexicon_store.py --corpus-id $cid --copies 3
    $store = switch ($cid) {
        'en-general' { 'lab/agent-stores/sss-en-general' }
        'en-tech' { 'lab/agent-stores/sss-en-tech' }
        'ru-general' { 'lab/agent-stores/sss-ru-general' }
        'ru-tech' { 'lab/agent-stores/sss-ru-tech' }
    }
    python tools/train_sss_nca_shards.py `
        --store-dir $store `
        --layer all `
        --device cuda `
        --epochs $epochs `
        --min-tokens 4
    python tools/nca_stale_shards.py --store-dir $store --sync-registry --dry-run
    python tools/sss_memory_manifest.py --store-dir $store --write
}

Write-Host "Done. Stores under lab/agent-stores/sss-*-general and sss-*-tech" -ForegroundColor Green
