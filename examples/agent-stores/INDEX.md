# Agent stores index

Structure names describe **role**, not ingest corpus.

| Store | Role | field_state | Notes |
|-------|------|-------------|--------|
| [sss-ru-lexicon-v0](sss-ru-lexicon-v0/) | **production** RU headword lexicon (sharded L2 + NCA) | see `MEMORY.md` | `nca/` under store; `lex_plan: corpus_quantile` |
| [sss-afan-v0](sss-afan-v0/) | **ingest ref** Afan 624 monolith | ~467 MiB | read-only; corpus source only |
| [sss-shard-smoke-v0](sss-shard-smoke-v0/) | kolobok smoke | ~1.8 MiB | dev |
| [sss-afan-iii-v0](sss-afan-iii-v0/) | sleep experiments (legacy) | optional | |

## Layout (every production store)

```text
sss-ru-lexicon-v0/
├── ltm/                       # compact memory (production ship)
│   ├── pack.manifest.json
│   └── l2/L2_word_07.ltm
├── nca/
│   ├── L1_syllable/model.pt
│   └── L2_word_07/model.pt
├── field_state.json           # lab only (~400 MiB); rebuild from ltm if needed
├── memory_manifest.json
└── MEMORY.md
```

**Поставка:** `ltm/` + `nca/` (~3 MiB + ~130 MiB NCA). Без `field_state.json` в дистрибутиве — см. `design/CASA-ADR-0002-agent-memory-ltm-nca.md`.

```bash
python tools/export_ltm_pack_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0
python tools/import_ltm_pack_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 --write
```

NCA weights **only** under `{store}/nca/` — not `examples/nca_out_afan_*`.

## Commands

```bash
python tools/remigrate_l2_lex_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0
python tools/train_sss_nca_shards_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 --device cuda
# defaults: windowed 16×16/stride 8 on 32², 80 ep/shard — see design/nca-train-defaults.v0.json
python tools/sss_memory_manifest_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 --write
```

Full pipeline: `scripts/run_sss_ru_lexicon_v0.ps1`

## Exp L0 smoke (ltm boot + F0 math)

```bash
# Boot from ltm/ only (~1.5 s, no 600 MiB field_state)
python tools/store_boot_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 --smoke

# F0_schema ingest + schema@1 bench (field-only, no claim.text)
python tools/bench_math_schema_v0.py \
  --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --bundle examples/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json \
  --cues examples/exp_l_v0/math_schema_cues.v1.json

# Persist F0 on field_state (optional)
python tools/f0_math_ingest_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --bundle examples/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json --boot-ltm-only --write
```

См. `design/f0-math-logical-layer-v0.md`, `design/understanding-contract-v0.md` (UC v0.1: `claims_nav_enabled` в `cen_plan`).

Regenerate map: `python tools/sss_memory_manifest_v0.py --store-dir <path> --write`
