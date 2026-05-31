# Agent stores index

**Каталог (оси locale / tier / corpus):** [`catalog.v0.json`](catalog.v0.json) — см. [`design/agent-store-catalog-v0.md`](../../design/agent-store-catalog-v0.md).  
**Контекст (ось + цепочка вывода):** [`design/context-axis-v0.md`](../../design/context-axis-v0.md).

Structure names describe **role**, not ingest corpus.

| Store | Role | field_state | Notes |
|-------|------|-------------|--------|
| [sss-ru-lexicon-v0](sss-ru-lexicon-v0/) | **archaic** RU (Afanasyev dialect L2 + NCA) | see `MEMORY.md` | lab only; prod → `sss-ru-general-v0` (modern) |
| [sss-en-folk-v0](sss-en-folk-v0/) | **EN folk** lexicon (Grimm + Jacobs) | `field_state` + `ltm/` | `L2_en_word_*` shards; hub links via linked boot |
| [sss-afan-v0](sss-afan-v0/) | **ingest ref** Afan 624 monolith | ~467 MiB | read-only; corpus source only |
| [sss-shard-smoke-v0](sss-shard-smoke-v0/) | kolobok smoke | ~1.8 MiB | dev |
| [sss-afan-iii-v0](sss-afan-iii-v0/) | sleep experiments (legacy) | optional | |
| [control-lab-v0](control-lab-v0/) | **control stack** DMN/SN/FPN/CEN | `prism_control` + `ltm/ctrl/` | `run_control_stack_migrate_v0.ps1` |

### Control lattice stack

```bash
python tools/migrate_control_stack_v0.py --store-dir <store> --bundle <bundle.json> --export-ltm
python tools/bench_control_stack_v0.py --store-dir lab/agent-stores/control-lab-v0
```

Design: [`design/control-lattice-stack-v0.md`](../../design/control-lattice-stack-v0.md).

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
python tools/export_ltm_pack_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0
python tools/import_ltm_pack_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --write
```

NCA weights **only** under `{store}/nca/` — not `lab/nca_out_afan_*`.

## Commands

```bash
python tools/remigrate_l2_lex_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0
python tools/train_sss_nca_shards_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --device cuda
# defaults: windowed 16×16/stride 8 on 32², 80 ep/shard — see design/nca-train-defaults.v0.json
python tools/sss_memory_manifest_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --write
```

Full pipeline: `scripts/run_sss_ru_lexicon_v0.ps1`

## Exp L0 smoke (ltm boot + F0 math)

```bash
# Boot from ltm/ only (~1.5 s, no 600 MiB field_state)
python tools/store_boot_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --smoke

# F0_schema ingest + schema@1 bench (field-only, no claim.text)
python tools/bench_math_schema_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --bundle lab/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json \
  --cues lab/exp_l_v0/math_schema_cues.v1.json

# Exp L0 predict loop: schema modality + critic (UC v0.6)
python tools/bench_schema_predict_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --bundle lab/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json \
  --cues lab/exp_l_v0/schema_predict_cues.v1.json

# Persist F0 on field_state (optional; run from repo root)
python tools/f0_math_ingest_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --bundle lab/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json --boot-ltm-only --write
```

См. `design/f0-math-logical-layer-v0.md`, `design/understanding-contract-v0.md` (UC v0.1: `claims_nav_enabled` в `cen_plan`).

## Exp T9 / Predictor smoke (UC v0.5)

```bash
# Segment predict + critic (field intuition)
python tools/bench_predict_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --cues lab/exp_t9_v0/segment_predict_cues.v1.json

# T9 prefix disambiguation on L2 lexicon
python tools/bench_t9_predict_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --cues lab/exp_t9_v0/t9_prefix_cues.v1.json

# Letter-by-letter T9 tick loop (UC v0.6)
python tools/bench_predict_tick_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --cues lab/exp_t9_v0/t9_tick_cues.v1.json

# Manual anchor cues + lexicon sweep (optional)
python tools/bench_t9_lexicon_sweep_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --manual-cues lab/exp_t9_v0/t9_manual_cues.v1.json \
  --sample 200

# Lexicon miss → cold ingest → predict again (offline headwords v0)
python tools/bench_lexicon_cold_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --cues lab/exp_t9_v0/lexicon_cold_cues.v1.json \
  --headwords lab/exp_t9_v0/lexicon_cold_headwords.v1.txt

# NCA stale shards: cold ingest queues pending → dry-run detect (no CUDA train)
python tools/bench_nca_stale_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --headwords lab/exp_t9_v0/lexicon_cold_headwords.v1.txt \
  --min-tokens 1

# Incremental sleep repair: train only stale L2 shards (default 25 epochs)
python tools/nca_stale_shards_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --sync-registry --dry-run

# VK layouts on field (L0_vk_map core ltm)
python tools/vk_layout_ingest_v0.py
python tools/bench_vk_layout_field_v0.py
python tools/bench_layout_parity_v0.py
dotnet test apps/Casa.Act.Core.Tests
```

См. `design/predictor-v0.md`, `design/experiment-t9-predictive-words-v0.md`.

## Exp bilingual v0 (EN + entity hub)

Separate stores: **RU** `sss-ru-lexicon-v0`, **EN folk** `sss-en-folk-v0` (Grimm + Jacobs, full headword list including articles).

```bash
# 1. Create EN folk store (~6700 headwords, batch L2, no stopword filter)
python tools/init_en_folk_store_v0.py \
  --headwords lab/exp_bilingual_v0/en_folk_headwords.v1.txt

# 2. Linked boot + entity hub (L3 only; L2 stays on each store)
python tools/bench_bilingual_linked_v0.py \
  --ru-store lab/agent-stores/sss-ru-lexicon-v0 \
  --en-store lab/agent-stores/sss-en-folk-v0 \
  --bundle lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json

python tools/bench_grapheme_clusters_v0.py \
  --cues lab/exp_bilingual_v0/grapheme_cluster_cues.v1.json
```

Dev overlay on RU store (legacy lab):

```bash
# See lab/exp_bilingual_v0/README.md
python tools/bench_entity_hub_v0.py \
  --store-dir lab/agent-stores/sss-ru-lexicon-v0 \
  --bundle lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json
```

Regenerate map: `python tools/sss_memory_manifest_v0.py --store-dir <path> --write`

## Agent profiles

Один CASA core, разные продукты = **exported agent store** (`ltm/` + `nca/`) + **profile JSON**.

| Doc | Роль |
|-----|------|
| [`design/CASA-ADR-0007-agent-profile-store-packs.md`](../../design/CASA-ADR-0007-agent-profile-store-packs.md) | канон |
| [`lab/agent-profiles/`](../agent-profiles/) | `bilingual-t9-console-v0`, `dev-ide-complete-v0` |

```bash
# Export перед поставкой (канон)
python tools/export_ltm_pack_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0
python tools/export_ltm_pack_v0.py --store-dir lab/agent-stores/sss-en-folk-v0
```

Planned: `run_agent_profile_v0.py`
