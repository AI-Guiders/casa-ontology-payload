# L3 phrase lattice sharding

**Status:** lab v0 (`phrase_shard.py`, `l3_remigrate.py`)  
**Date:** 2026-06-01  
**Parent:** [`l2-lattice-sharding.md`](l2-lattice-sharding.md), [`sss-layer-names.md`](sss-layer-names.md)

## Problem

Monolith `L3_phrase` holds all field tokens (entities, scenes, links, `W:`, …). On ingest-ref-afan **vocab > 65535** (ltm v0 u16) — export/migrate skips the lattice.

## Model

Same as L2: **connected network**, one NCA per shard where trained.

```text
L2_word_* ──bind──► L3_phrase_00 … L3_phrase_63
```

## Shard routing (v0)

| Key | Value |
|-----|--------|
| `num_shards` | 64 (default) |
| `legacy` | `L3_phrase` — read merge; cleared after remigrate |
| `mode` | lexicographic **corpus_quantile** on sorted **token strings** |
| `token_index[token] → L3_phrase_XX` | fast route after remigrate |

Remigrate **copies (x,y) placements** from monolith (does not re-listen).

## Kernel API

- `needs_l3_remigrate` / `ensure_l3_sharded_for_export` — export, sleep `ltm_layout` aspect
- `field_state.l3_sharding` — plan + index (like `l2_sharding`)

CLI (lab): `python tools/remigrate_l3_phrase.py --store-dir … --write`

## Semantic shard ids (token_range)

Like L2 `lexicon-ru-{word_lo}-{word_hi}`:

| Field | Value |
|-------|--------|
| **Canonical id** | `phrases-{token_lo_slug}-{token_hi_slug}` (~20+20 chars from field token heads) |
| **Numeric idx** | `token_ranges[].shard` only (sort key `#07` in MEMORY.md — **not** in id) |
| **Label** | full `E:lang.word.*\|…` heads in manifest `label` + hint `entity/word/meta` |
| **Tool** | `python tools/rename_phrase_shards_semantic.py --store-dir … --write-memory` |

Interim v1 kebab `phrases-07` (migrate-only) is superseded by token-range slugs on production stores.

## Not in v0

- Auto-split when a single shard exceeds u16 (bump `num_shards` + re-shard manually)
