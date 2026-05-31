# `tools/` — legacy CLI paths (M2 layout)

**Все реализации** живут в **`casa/`**; здесь только **shims** (`sys.modules` alias) и `_shim_v0.py`.

Канон: [`design/prism-layout-and-naming-v1.md`](../design/prism-layout-and-naming-v1.md), [`design/CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](../design/CASA-ADR-0012-cide-parity-fieldbus-and-migration.md).

## Структура `casa/`

```
casa/
  _paths.py                 REPO_ROOT + tools/ на sys.path
  prisms/
    shared/                 codec, field I/O, store layout, NCA train, migrations
    memory/                 sss_*, orthography, lexicon, ingest
    hippo/                  wake / sleep / replay / repair
    control/                DMN stack, SN/CEN tick, control NCA train
    tick/                   unified tick, T9 runtime, predictor, surface error
  cli/
    bench/                  bench_* scripts
    init_*, train_*, exp_*   one-off lab CLIs
tools/
  *.py                      shim → casa.* (имя модуля сохранено для CI/scripts)
  _shim_v0.py               (legacy helper; shims inline import_module)
scripts/
  migrate_tools_to_casa.py  batch migrator + `reshim-all`
```

## Использование

```powershell
# CLI как раньше — путь не менялся
python tools/store_boot_v0.py --smoke ...
python tools/run_t9_demo_cycle_v0.py

# Импорт в коде — legacy имя или casa.*
from store_layout_v0 import repo_root
from casa.prisms.shared.store_layout_v0 import repo_root
```

## Мигратор

```powershell
python scripts/migrate_tools_to_casa.py list          # размеры батчей
python scripts/migrate_tools_to_casa.py shared-core     # один батч
python scripts/migrate_tools_to_casa.py reshim-all    # перегенерить shims
```

## M4 (ещё не сделано)

- [x] CI: `scripts/check_tools_shims.py` — все `tools/*.py` = shims
- [ ] `check_tools_shims.py --strict-casa-imports` green (casa/ без legacy imports)
- [ ] `pyproject` console_scripts → удалить shims
- [ ] Re-export `sss-ru-general-v0` ltm/ на canonical-only (опционально legacy mirror off)

Тесты: **`tests/`** (не в `tools/`).
