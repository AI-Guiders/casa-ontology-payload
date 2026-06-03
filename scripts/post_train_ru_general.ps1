# Wait for stale NCA train on lexicon-ru-general, then cartridge + control rollout + commits.
# Log/status: post_train_ru_general.{log,status.json}  Lock: post_train_ru_general.lock
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$Store = 'lab/agent-stores/lexicon-ru-general'
$ControlLab = 'lab/agent-stores/control-lab'
$Log = Join-Path $Root 'post_train_ru_general.log'
$Status = Join-Path $Root 'post_train_ru_general.status.json'
$Lock = Join-Path $Root 'post_train_ru_general.lock'
$PollSec = 90

if (Test-Path $Lock) {
    Write-Host "post_train already running (lock exists)"
    exit 0
}
Set-Content -Path $Lock -Value ("pid={0} started={1}" -f $PID, (Get-Date -Format 'o')) -Encoding utf8

function Write-Log([string]$Msg) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Msg
    $line | Out-File -FilePath $Log -Append -Encoding utf8
    Write-Host $line
}

function Set-Status([hashtable]$Fields) {
    $obj = [ordered]@{ updated_at = (Get-Date).ToUniversalTime().ToString('o') }
    foreach ($k in $Fields.Keys) { $obj[$k] = $Fields[$k] }
    ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $Status -Encoding utf8
}

function Get-StaleCount {
    $json = python tools/nca_stale_shards.py --store-dir $Store --dry-run 2>&1
    if ($LASTEXITCODE -ne 0) { throw "dry-run failed: $json" }
    return ([int]($json | ConvertFrom-Json).stale_count)
}

function Test-TrainRunner {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'nca_stale_shards\.py' -and $_.CommandLine -match '--train' } |
        Select-Object -First 1
}

function Invoke-GitCommit([string]$Message, [string[]]$Paths) {
    if ($Paths.Count -eq 0) { return $false }
    git add @Paths
    if (-not (git diff --cached --quiet 2>$null)) {
        git commit -m $Message
        if ($LASTEXITCODE -ne 0) { throw "git commit failed: $Message" }
        return $true
    }
    git reset HEAD 2>$null | Out-Null
    return $false
}

try {
    Write-Log '=== post_train_ru_general started (cartridge + rollout + control NCA) ==='
    Set-Status @{ phase = 'waiting_train'; stale_count = (Get-StaleCount) }

    while ($true) {
        $stale = Get-StaleCount
        $runner = Test-TrainRunner
        Set-Status @{
            phase            = 'waiting_train'
            stale_count      = $stale
            train_runner_pid = $(if ($runner) { $runner.ProcessId } else { $null })
        }
        if ($stale -eq 0 -and -not $runner) { break }
        Write-Log ("poll stale={0} train_runner={1}" -f $stale, $(if ($runner) { $runner.ProcessId } else { 'none' }))
        Start-Sleep -Seconds $PollSec
    }

    Write-Log '=== train complete (stale=0) ==='
    Set-Status @{ phase = 'export'; stale_count = 0 }

    Write-Log 'export_ltm_pack'
    python tools/export_ltm_pack.py --store-dir $Store
    if ($LASTEXITCODE -ne 0) { throw 'export_ltm_pack failed' }

    Write-Log 'lexicon_memory_manifest --write'
    python tools/lexicon_memory_manifest.py --store-dir $Store --write
    if ($LASTEXITCODE -ne 0) { throw 'lexicon_memory_manifest failed' }

    Write-Log 'store_boot --smoke'
    python tools/store_boot.py --store-dir $Store --smoke
    if ($LASTEXITCODE -ne 0) { throw 'store_boot smoke failed' }

    Set-Status @{ phase = 'git_cartridge'; smoke = 'ok' }
    Write-Log '=== git: cartridge ==='

    $absPathFiles = @(
        'tools/export_ltm_pack.py',
        'tools/grapheme_glyph_export.py',
        'lab/exp_bilingual/fonts/README.md'
    )
    $absChanged = @($absPathFiles | Where-Object { (git status --short $_ 2>$null) -match '^\s*M' })
    if ($absChanged.Count -gt 0) {
        if (Invoke-GitCommit @"
fix(store): repo-relative paths in export and font fallbacks

Use rel_to_repo for NCA model_path in ltm export; resolve Windows fonts via WINDIR.
"@ $absChanged) {
            Write-Log ('committed abs-path: ' + ($absChanged -join ', '))
        }
    }

    $cartridgePaths = @(
        "$Store/ltm",
        "$Store/nca/words-ru-*",
        "$Store/nca/train_shards_report.json",
        "$Store/nca_train_registry.json",
        "$Store/MEMORY.md",
        "$Store/memory_manifest.json"
    )
    git reset HEAD -- "$Store/nca/L2_word_" 2>$null | Out-Null
    if (Invoke-GitCommit @"
feat(store): refresh lexicon-ru-general L2 NCA after field_version drift

Incremental stale retrain (words-ru-* @ fv=5): export ltm pack, manifest, boot smoke OK.
"@ $cartridgePaths) {
        Write-Log 'cartridge commit OK'
    }
    else {
        Write-Log 'cartridge commit: nothing to commit'
    }

    Write-Log '=== control rollout (prism_control migrate + bench) ==='
    Set-Status @{ phase = 'rollout' }

    Write-Log 'migrate_control_stack --export-ltm'
    python tools/migrate_control_stack.py --store-dir $Store --export-ltm
    if ($LASTEXITCODE -ne 0) {
        Write-Log 'migrate failed; retry seed-only (no bundle required after CLI fix)'
        throw 'migrate_control_stack failed'
    }

    Write-Log 'bench_control_stack (ru-general)'
    python tools/bench_control_stack.py --store-dir $Store --structure-only
    if ($LASTEXITCODE -ne 0) { throw 'bench_control_stack ru-general failed' }

    if (Test-Path (Join-Path $ControlLab 'field_state.json')) {
        $labBench = python tools/bench_control_stack.py --store-dir $ControlLab --structure-only 2>&1 | ConvertFrom-Json
        if ($labBench.missing.Count -gt 0) {
            Write-Log ("bench_control_stack (control-lab) skipped: missing {0}" -f ($labBench.missing -join ', '))
        }
        else {
            Write-Log 'bench_control_stack (control-lab, structure-only)'
            if (-not $labBench.pass) { throw 'bench_control_stack control-lab failed' }
        }
    }

    Write-Log 're-export after control migrate'
    python tools/export_ltm_pack.py --store-dir $Store
    python tools/lexicon_memory_manifest.py --store-dir $Store --write

    Set-Status @{ phase = 'git_rollout'; rollout_bench = 'ok' }
    Write-Log '=== git: control rollout ==='

    $rolloutPaths = @(
        "$Store/ltm/ctrl",
        "$Store/MEMORY.md",
        "$Store/memory_manifest.json",
        'scripts/post_train_ru_general.ps1'
    )
    if (Invoke-GitCommit @"
feat(control): rollout prism_control stack on lexicon-ru-general

Migrate control lattices to field + ltm/ctrl; bench_control_stack green.
"@ $rolloutPaths) {
        Write-Log 'rollout commit OK'
    }
    else {
        Write-Log 'rollout commit: nothing to commit'
    }

    Write-Log '=== GPU control NCA (lattice_predict, lattice_dan, lattice_value) ==='
    Set-Status @{ phase = 'train_control_nca'; rollout = 'ok' }

    python tools/train_control_nca_stack.py --store-dir $Store --device cuda
    if ($LASTEXITCODE -ne 0) { throw 'train_control_nca_stack failed' }

    Write-Log 're-export + bench after control NCA'
    python tools/export_ltm_pack.py --store-dir $Store
    python tools/lexicon_memory_manifest.py --store-dir $Store --write
    python tools/bench_control_stack.py --store-dir $Store --structure-only
    if ($LASTEXITCODE -ne 0) { throw 'bench_control_stack after NCA failed' }

    Set-Status @{ phase = 'git_control_nca'; control_nca = 'ok' }
    Write-Log '=== git: control NCA weights ==='

    $controlNcaPaths = @(
        "$Store/nca/lattice_predict",
        "$Store/nca/lattice_dan",
        "$Store/nca/lattice_value",
        "$Store/ltm/ctrl",
        "$Store/nca_train_registry.json",
        "$Store/MEMORY.md",
        "$Store/memory_manifest.json",
        'tools/train_sss_nca.py',
        'tools/train_control_nca_stack.py',
        'scripts/post_train_ru_general.ps1'
    )
    if (Invoke-GitCommit @"
feat(control): train predict/dan/value NCA on lexicon-ru-general (ADR-0010)

GPU windowed train on prism_control lattices; export ltm/ctrl + registry update.
"@ $controlNcaPaths) {
        Write-Log 'control NCA commit OK'
    }
    else {
        Write-Log 'control NCA commit: nothing to commit'
    }

    $head = git rev-parse --short HEAD
    Write-Log ("=== done HEAD={0} ===" -f $head)
    Set-Status @{
        phase       = 'done'
        head        = $head
        stale_count = 0
        smoke       = 'ok'
        rollout     = 'ok'
        control_nca = 'ok'
    }
}
catch {
    Write-Log ("ERROR: $_")
    Set-Status @{ phase = 'error'; error = $_.ToString() }
    exit 1
}
finally {
    Remove-Item -Path $Lock -Force -ErrorAction SilentlyContinue
}
