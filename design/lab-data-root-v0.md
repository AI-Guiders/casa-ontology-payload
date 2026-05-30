# Lab data root (`lab/`)

**Date:** 2026-05-30  
**Status:** accepted  

Каталог **`lab/`** (ранее `examples/`) — данные и поставки CASA lab, не tutorial-примеры.

| Подкаталог | Роль |
|------------|------|
| `agent-stores/` | agent store packs (`ltm/`, `nca/`, опц. `field_state.json`) |
| `agent-core/` | shared immutable core (`alphabet-v0`, `vk-layouts-v0`, …) |
| `agent-profiles/` | JSON-рецепты boot |
| `corpus/` | источники ingest (headwords, seed) |
| `kb/`, `exp_*`, `nca_out*` | бандлы, эксперименты, артефакты прогонов |

Канон путей в коде: `tools/store_layout_v0.py` → `LAB_DATA_DIR = "lab"`.
