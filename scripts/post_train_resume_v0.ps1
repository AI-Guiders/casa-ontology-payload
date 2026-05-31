# Resume post-train from control rollout (L2 cartridge already committed).
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUTF8 = '1'
$Store = 'lab/agent-stores/sss-ru-general-v0'
$Log = Join-Path $Root 'post_train_ru_general.log'

function Write-Log([string]$Msg) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Msg
    $line | Out-File -FilePath $Log -Append -Encoding utf8
    Write-Host $line
}

function Set-Status([hashtable]$Fields) {
    $Status = Join-Path $Root 'post_train_ru_general.status.json'
    $obj = [ordered]@{ updated_at = (Get-Date).ToUniversalTime().ToString('o') }
    foreach ($k in $Fields.Keys) { $obj[$k] = $Fields[$k] }
    ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $Status -Encoding utf8
}

try {
    Write-Log '=== resume: rollout + control NCA ==='
    Set-Status @{ phase = 'rollout' }

    python tools/bench_control_stack_v0.py --store-dir $Store --structure-only
    if ($LASTEXITCODE -ne 0) { throw 'bench structure failed' }

    python tools/export_ltm_pack_v0.py --store-dir $Store
    python tools/sss_memory_manifest_v0.py --store-dir $Store --write

    git add "$Store/ltm/ctrl" tools/migrate_control_stack_v0.py tools/bench_control_stack_v0.py `
        "$Store/MEMORY.md" "$Store/memory_manifest.json" scripts/post_train_resume_v0.ps1
    git diff --cached --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        git commit -m "feat(control): rollout prism_control on sss-ru-general-v0 (seed stack)"
    }

    Write-Log 'train_control_nca_stack_v0 cuda'
    Set-Status @{ phase = 'train_control_nca' }
    python tools/train_control_nca_stack_v0.py --store-dir $Store --device cuda
    if ($LASTEXITCODE -ne 0) { throw 'control NCA train failed' }

    python tools/export_ltm_pack_v0.py --store-dir $Store
    python tools/sss_memory_manifest_v0.py --store-dir $Store --write
    python tools/bench_control_stack_v0.py --store-dir $Store --structure-only

    git add "$Store/nca/lattice_predict" "$Store/nca/lattice_dan" "$Store/nca/lattice_value" `
        "$Store/ltm/ctrl" "$Store/nca_train_registry.v0.json" tools/train_sss_nca_v0.py `
        tools/train_control_nca_stack_v0.py "$Store/MEMORY.md" "$Store/memory_manifest.json"
    git diff --cached --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        git commit -m "feat(control): train predict/dan/value NCA on sss-ru-general-v0"
    }

    $head = git rev-parse --short HEAD
    Write-Log "=== resume done HEAD=$head ==="
    Set-Status @{ phase = 'done'; head = $head; rollout = 'ok'; control_nca = 'ok' }
}
catch {
    Write-Log "ERROR: $_"
    Set-Status @{ phase = 'error'; error = $_.ToString() }
    exit 1
}
