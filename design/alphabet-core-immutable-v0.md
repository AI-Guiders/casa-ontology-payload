# Immutable alphabet core (RU 33 + EN 26)

**Date:** 2026-05-30  
**Status:** lab  
**Pack:** `lab/agent-core/alphabet-v0/ltm/`

## Две решётки L0

| Script | Lattice | Count | `concept_id` |
|--------|---------|-------|----------------|
| RU cyrl | **`L0_grapheme_cyrl`** | 33 | `grapheme.cyrl.{буква}` |
| EN latn | **`L0_grapheme_latn`** | 26 | `grapheme.latn.{a-z}` |

Отдельные 32×32 — RU/EN не делят одну решётку. Boot грузит **весь** alphabet pack (locale-only split не используем).

## Stack

`design/sss-lattice-stack.v0.toml` — `z_bridge_L0cyrl_L1`, `z_bridge_L0latn_L1` → `L1_syllable`.

## Миграция (один раз)

Старый монолит `L0_grapheme`:

```bash
python tools/migrate_l0_grapheme_split_v0.py
python tools/vk_layout_ingest_v0.py   # пересобрать vk-layouts core
```

## Команды

```bash
python tools/build_alphabet_core_ltm_v0.py
python tools/bench_alphabet_core_v0.py
```

## Boot

`merge_core_ltm_stack` — alphabet (2× L0), затем VK (`L0_vk_map` + grapheme overlay на cyrl/latn).

Пустой L0 в lab store после split:

```bash
python tools/boot_alphabet_into_stores_v0.py --compact
```

## VK NCA

```bash
python tools/vk_nca_train_v0.py --device cuda
```

PowerShell: `scripts/run_alphabet_boot_stores_v0.ps1`
