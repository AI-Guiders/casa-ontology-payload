# Memory hierarchy (agent store) — KB-like index

**Status:** v0 (`memory_manifest.py`)  
**Date:** 2026-05-30  
**See:** [`l2-lattice-sharding.md`](l2-lattice-sharding.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md)

## Tree (analog of KB folders)

```text
agent-store/{id}/              # e.g. sss-ru-lexicon (not corpus name)
├── MEMORY.md                 ← human map (generated)
├── memory_manifest.json      ← machine map (generated)
├── field_state.json          ← **runtime checkpoint** (prism_hippo queue, SN meta; not in profile tar)
├── agent_session.json        ← runtime checkpoint (FPN WM)
├── ltm/                      ← **shipped** profile pack (ship + nca/)
│   ├── pack.manifest.json
│   └── l2/L2_word_07.ltm
├── nca/                      ← canonical NCA registry (one model.pt per lattice)
│   ├── L1_syllable/model.pt
│   ├── L2_word_07/model.pt
│   └── train_shards_report.json
├── ingest_log.ndjson         ← optional: corpus sources (Afan, bukvar, …)
├── journal/                  ← agent-owned prose (NOT in ltm/ export)
│   ├── index.json
│   └── math/entries.jsonl
├── agent/                    ← agent-owned prism (lattices + nca; NOT in ltm/ export)
│   ├── manifest.json
│   ├── lattices/
│   └── nca/
└── _parallel_shards/         ← ingest worker artifacts (optional)
```

Do **not** use `lab/nca_out_<corpus>_*/` for production — train in-place under `{store}/nca/` (`train_memory_nca_shards.py` default).

## Store tiers (canon)

Три имени на диске — **не** «new» и не смешивать с profile export.

| Tier | Имя | Пути | Cold boot из `ltm/` | В profile tar | Flush после wake/tick/sleep |
|------|-----|------|---------------------|---------------|----------------------------|
| **Shipped** | profile pack | `ltm/`, `nca/` | **да** — memory + control + NCA | **да** | `export_ltm_pack` |
| **Runtime** | checkpoint | `field_state.json`, `agent_session.json` | **нет** — hippo queue пуст до wake | **нет** | `save_runtime_state` |
| **Self** | agent-owned | `agent/`, `journal/` | load если каталог есть | **нет** (opt-in backup) | `save_agent_prism`, journal CLI |

```text
  Shipped (ltm/ + nca/)     ──cold boot──►  prism_memory + prism_control + NCA paths
         ▲                                      │
         │ sleep / export_ltm_pack              │ T_wake: append_episode
         │                                      ▼
  Runtime checkpoint          ◄──save_runtime_state──  prism_hippo + SN meta
  (field_state, session)

  Self (agent/, journal/)     ◄── agent_remember ──  не в ltm/ без agent_promote
```

**Hippo:** wake пишет в **runtime checkpoint**; после **sleep** consolidated knowledge уходит в **shipped** (`prism_memory` → `ltm/`), episodic queue **prune** — не дублировать в profile tar как dump эпизодов.

**Код:** константы `STORE_TIER_*` в `casa/prisms/shared/store_layout.py`; flush — `casa/prisms/shared/store_persist.py`.

**Неявная vs явная память:** [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md) § Неявная vs явная — tick/hippo/поле vs `agent_remember`.

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
    ├── H1_surface … H3_scene   # design/hippo-lattice-stack.md
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
python tools/memory_manifest.py --store-dir lab/agent-stores/sss-ru-lexicon --write
```
