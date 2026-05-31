# Immutable alphabet core — per-language orthography (L0)

**Date:** 2026-05-30 (updated 2026-05-31)  
**Status:** lab  
**Pack:** `lab/agent-core/alphabet-v0/ltm/`  
**Naming:** KB `kb-casa-lattice-naming-v1.md` · lab mirror [`lattice-naming-v1.md`](lattice-naming-v1.md)

## Алфавит = язык, не «вся кириллица»

| locale | Lattice (v1) | Legacy | Буквы (суть) | `concept_id` (lab) |
|--------|--------------|--------|--------------|-------------------|
| **ru** | **`alphabet-ru`** | `L0_grapheme_cyrl` | 33, **нет і** | `grapheme.cyrl.*` |
| **en** | **`alphabet-en`** | `L0_grapheme_latn` | 26 a–z | `grapheme.latn.*` |
| **uk** | **`alphabet-uk`** | — (roadmap) | **і**, **ї**, **є**, **ґ**; ≠ ru | TBD |
| **be** | **`alphabet-be`** | — (roadmap) | свой набор | TBD |

**script** (`cyrl`, `latn`, …) — **метаданные** (Unicode-семейство, раскладки). **Решётка L0** — **orthography locale**: RU и UK оба cyrl, но **разные** `alphabet-*`.

Отдельная 32×32 на язык — RU store не делит L0 с UK.

## Stack

`design/sss-lattice-stack.v1.toml` — мосты `bridge-alphabet-{locale}-syllables-{locale}`.

## Миграция (один раз)

```bash
python tools/migrate_l0_grapheme_split_v0.py
python tools/vk_layout_ingest_v0.py
```

`L0_grapheme_cyrl` → rename target **`alphabet-ru`** (не «общий cyrl»).

## Команды

```bash
python tools/build_alphabet_core_ltm_v0.py
python tools/bench_alphabet_core_v0.py
python tools/boot_alphabet_into_stores_v0.py --compact
```

## VK NCA

```bash
python tools/vk_nca_train_v0.py --device cuda
```

PowerShell: `scripts/run_alphabet_boot_stores_v0.ps1`
