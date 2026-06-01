# L2 word lattice sharding — connected memory network

**Status:** lab v0 (`lexicon_shard.py`)  
**Date:** 2026-05-30  
**Parent:** [`sss-multi-lattice-z.md`](sss-multi-lattice-z.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md)

## Problem

Single `L2_word` 32×32 holds the whole corpus (~41k words, ~86k lattice tokens).  
Decode/babble still works; **NCA repair** needs `k = |token_ids|` channels — not feasible on one grid.

## Model (both true)

1. **Memory = connected network** of lattices (z-bridges, hippo, scene links).
2. **Each lattice (shard) = own NCA** for local repair/regrow on sleep.

```text
L1_syllable ──compose──► L2_word_00 … L2_word_63 ──bind──► L3_phrase
                              │              │
                         model_00.pt    model_63.pt
```

## Shard routing (v0)

| Key | Value |
|-----|--------|
| `num_shards` | 64 (default) |
| `shard_id` | `lexicon-ru_{idx:02d}` (v1 kebab: `lexicon-ru-07`) |
| `mode` | **`lexicographic`** (default) or `hash` (legacy) |
| `lex_plan` | **`corpus_quantile`** (default) or `alpha` (fallback) |
| `idx` (lex, corpus) | sort all headwords → **equal-count bins** in dictionary order; label `авось–агнец` |
| `idx` (lex, alpha) | slice alphabet string (may have empty «ь/ы» shelves — avoid in prod) |
| `idx` (hash) | `crc32(norm_word) % num_shards` |
| `legacy` | `L2_word` — read + babble merge; no new writes when sharding enabled |

`field_state.l2_sharding.word_index[word] → shard_id` — fast route after first listen.  
`letter_ranges[]` + `lex_shard_starts[]` — machine + human map (`MEMORY.md`).  
`initial_letter_counts` — only **attested** word-initial letters in corpus (no «ь» shelf if no words).

**Corpus is not structure:** Afanasyev / bukvar are ingest **sources** only; L2 layout follows the dictionary, not tale names.

Re-shard: `python tools/remigrate_l2_lex.py --store-dir …` (builds quantile plan from headwords).

## Babble / decode

- Virtual layer **`L2_word`**: merge ranked concepts from **legacy + all shards**.
- Cue `волк` → route to shard → exact-match boost (see `rank_for_cue`).

## NCA registry

```json
"nca": {
  "models": {
    "L2_word_00": "<store>/nca/L2_word_00/model.pt",
    "L1_syllable": "<store>/nca/L1_syllable/model.pt"
  }
}
```

Train: `train_memory_nca_shards.py --store-dir … --layer L2_word`

## Not in v0

- Auto-split shard when token count > cap (manual num_shards bump).
- z_bridge per shard (compose still via bukvar on legacy or L2_word_00).

**L3 phrase sharding:** [`l3-lattice-sharding.md`](l3-lattice-sharding.md).
