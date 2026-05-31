# CASA ontology payload — Python layout (M2 migration)

**Статус:** `tools/` всё ещё содержит ~270 CLI-скриптов и legacy-модулей; канонический код переезжает в **`casa/prisms/`**. Старые пути — **shim** (`from casa… import *`), CI и `python tools/foo.py` не ломаются.

Канон: [`design/prism-layout-and-naming-v1.md`](../design/prism-layout-and-naming-v1.md), фазы M0–M4 в [`design/CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](../design/CASA-ADR-0012-cide-parity-fieldbus-and-migration.md).

## Целевая структура

```
casa/
  _paths.py              # REPO_ROOT, tools/ на sys.path
  prisms/
    control/             # prism_control (DMN, SN, FPN, CEN, predict, DAN, value)
    memory/              # lexicon shards, math schema, orthography
    hippo/               # wake / sleep / episodic
    shared/              # lattice ids, store layout, field bus (roadmap)
tools/
  _shim_v0.py            # bootstrap для shims
  *.py                   # тонкие shims + ещё не перенесённые скрипты
```

## Перенесено (M2, in progress)

| Legacy `tools/` | Semantic home | Статус |
|-----------------|---------------|--------|
| `lattice_names_v1.py` | `casa.prisms.shared.lattice_names_v1` | **done** (shim) |
| `control_stack_v0.py` | `casa.prisms.control.stack_v0` | **done** |
| `control_cylinders_v0.py` | `casa.prisms.control.cylinders_v0` | **done** |
| `control_tick_v0.py` | `casa.prisms.control.tick_v0` | **done** |
| `control_predict_v0.py` | `casa.prisms.control.predict_v0` | **done** |
| `control_attention_v0.py` | `casa.prisms.control.attention_v0` | **done** |
| `control_value_v0.py` | `casa.prisms.control.value_v0` | **done** |

## Следующие очереди (не тронуто)

| Legacy | Target |
|--------|--------|
| `store_layout_v0.py`, `prism_state_v0.py`, `field_write.py` | `casa.prisms.shared.*` |
| `sss_cylinders_v0.py`, `sss_l2_shard_v0.py`, `sss_stack_v0.py`, … | `casa.prisms.memory.*` |
| `sss_wake_v0.py`, `sss_sleep_v0.py`, `sleep_replay_v0.py` | `casa.prisms.hippo.*` |
| `train_sss_nca_v0.py` | `casa.prisms.shared.nca_train` |
| `bench_*`, `init_*`, ingest | остаются в `tools/` как CLI или `casa/prisms/*/cli` |

## Как добавлять модуль

1. Реализация → `casa/prisms/<prism>/<name>_v0.py` (`ensure_import_paths()` + legacy imports из `tools/` пока нужно).
2. `tools/<legacy>.py` → shim через `_shim_v0.load_casa(...)`.
3. Строка в эту таблицу + pytest green.

**Не делать:** big-bang rename всех `sss_*` одним коммитом; удалять shims до grep-clean (M4).
