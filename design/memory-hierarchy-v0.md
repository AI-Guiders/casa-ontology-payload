# Memory hierarchy (agent store) — KB-like index

**Status:** v0 (`sss_memory_manifest_v0.py`)  
**Date:** 2026-05-30  
**See:** [`l2-lattice-sharding-v0.md`](l2-lattice-sharding-v0.md), [`multi-cylinder-memory-v0.md`](multi-cylinder-memory-v0.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md)

## Tree (analog of KB folders)

```text
agent-store/{id}/              # e.g. sss-ru-lexicon-v0 (not corpus name)
├── MEMORY.md                 ← human map (generated)
├── memory_manifest.json      ← machine map (generated)
├── field_state.json          ← live cylinder stack (lab / merge; optional in distro)
├── ltm/                      ← compact memory pack (ship this + nca/)
│   ├── pack.manifest.json
│   └── l2/L2_word_07.ltm
├── nca/                      ← canonical NCA registry (one model.pt per lattice)
│   ├── L1_syllable/model.pt
│   ├── L2_word_07/model.pt
│   └── train_shards_report.json
├── ingest_log.ndjson         ← optional: corpus sources (Afan, bukvar, …)
└── _parallel_shards/         ← ingest worker artifacts (optional)
```

Do **not** use `lab/nca_out_<corpus>_*/` for production — train in-place under `{store}/nca/` (`train_sss_nca_shards_v0.py` default).

## Logical hierarchy

```text
cylinders
├── prism_memory (SSS)
│   ├── L0_grapheme          [1 lattice, 1 NCA]
│   ├── L1_syllable          [1 lattice, 1 NCA]
│   ├── L2_word              [legacy monolith — read-only after migrate]
│   ├── L2_word_00 … _63     [64 shards, 1 NCA each]
│   └── L3_phrase
└── prism_hippo (episodic)
    ├── H1_surface … H3_scene   # design/hippo-lattice-stack-v0.md
    └── H0_episode (legacy → H1)
```

## field_state keys

| Key | Role |
|-----|------|
| `l2_sharding.mode` | `lexicographic` (default) or `hash` |
| `l2_sharding.lex_plan` | `corpus_quantile` (default): equal bins over sorted headwords |
| `l2_sharding.letter_ranges` | labels `word_lo–word_hi`, `word_count`, attested `initial_letters` |
| `l2_sharding.lex_shard_starts` | first headword per shard (routing) |
| `l2_sharding.initial_letter_counts` | only attested word-initial letters in corpus |
| `l2_sharding.word_index` | word → shard_id |
| `nca.models` | lattice_id → path to `model.pt` |
| `consolidation` | sleep history |

## Regenerate index

```bash
python tools/sss_memory_manifest_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --write
```
