# Agent stores index

**Каталог (оси locale / tier / corpus):** [`catalog.json`](catalog.json) · **lab roles:** [`catalog-lab-roles.md`](catalog-lab-roles.md) — см. [`design/agent-store-catalog.md`](../../design/agent-store-catalog.md).  
**Контекст (ось + цепочка вывода):** [`design/context-axis.md`](../../design/context-axis.md).

Structure names describe **role**, not ingest corpus.

## Lab stores (role-first — prefer over `sss-*` for new work)

| Store | Role | Default for |
|-------|------|-------------|
| [math-l0-lab](math-l0-lab/) | F0 / sticks / emergent ops | `bench_math_schema`, teacher `-` mint |
| [language-agent-lab](language-agent-lab/) | agent dialogue + journal | `agent_sn_cen_tick`, ortho «не кричи» |
| [control-lab](control-lab/) | prism_control stack | `bench_control_stack` |
| [code-agent-lab](code-agent-lab/) | IDE/code T9 | ADR-0007 autocomplete lab |
| [bukvar-lab](bukvar-lab/) | listen / bukvar | infancy phase 1–2 |
| [research-agent-lab](research-agent-lab/) | research bundles | ML import smoke |

**Migrate** misplaced runtime off prod lexicon:

```bash
python -m casa.cli migrate_agent_lab_stores
```

Init F0 lab only:

```bash
python -m casa.cli init_math_l0_lab
python -m casa.cli bench_schema_predict --store-dir lab/agent-stores/math-l0-lab \
  --bundle lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json
```

**Do not** run stick/emergent teacher on `sss-ru-general` — prod DetCorpus T9 cartridge.

## Lexicon / corpus stores (`sss-*` legacy folder names)

| Store | Role | field_state | Notes |
|-------|------|-------------|--------|
| [sss-ru-lexicon](sss-ru-lexicon/) | **archaic** RU (Afanasyev dialect L2 + NCA) | see `MEMORY.md` | lab only; prod → `sss-ru-general` (modern) |
| [sss-en-folk](sss-en-folk/) | **EN folk** lexicon (Grimm + Jacobs) | `field_state` + `ltm/` | `L2_en_word_*` shards; hub links via linked boot |
| [sss-afan](sss-afan/) | **ingest ref** Afan 624 monolith | ~467 MiB | read-only; corpus source only |
| [sss-shard-smoke](sss-shard-smoke/) | kolobok smoke | ~1.8 MiB | dev |
| [sss-afan-iii](sss-afan-iii/) | sleep experiments (legacy) | optional | |
| [control-lab](control-lab/) | **control stack** DMN/SN/FPN/CEN | `prism_control` + `ltm/ctrl/` | `run_control_stack_migrate.ps1` |

### Control lattice stack

```bash
python tools/migrate_control_stack.py --store-dir <store> --bundle <bundle.json> --export-ltm
python tools/bench_control_stack.py --store-dir lab/agent-stores/control-lab
```

Design: [`design/control-lattice-stack.md`](../../design/control-lattice-stack.md).

## Layout (every production store)

```text
sss-ru-lexicon/
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
python tools/export_ltm_pack.py --store-dir lab/agent-stores/sss-ru-lexicon
python tools/import_ltm_pack.py --store-dir lab/agent-stores/sss-ru-lexicon --write
```

NCA weights **only** under `{store}/nca/` — not `lab/nca_out_afan_*`.

## Commands

```bash
python tools/remigrate_l2_lex.py --store-dir lab/agent-stores/sss-ru-lexicon
python tools/train_memory_nca_shards.py --store-dir lab/agent-stores/sss-ru-lexicon --device cuda
# defaults: windowed 16×16/stride 8 on 32², 80 ep/shard — see design/nca-train-defaults.json
python tools/memory_manifest.py --store-dir lab/agent-stores/sss-ru-lexicon --write
```

Full pipeline: `scripts/run_sss_ru_lexicon.ps1`

## Exp L0 smoke (ltm boot + F0 math)

**Store:** `math-l0-lab` (canonical). Legacy alias: `sss-ru-lexicon` still works for old scripts.

```bash
python -m casa.cli init_math_l0_lab

# Boot from ltm/ only (~1.5 s, no 600 MiB field_state)
python -m casa.cli store_boot --store-dir lab/agent-stores/math-l0-lab --smoke

# F0_schema ingest + schema@1 bench (field-only, no claim.text)
python -m casa.cli bench_math_schema \
  --store-dir lab/agent-stores/math-l0-lab \
  --bundle lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json \
  --cues lab/exp_l/math_schema_cues.v1.json

# Exp L0 predict loop: schema modality + critic (UC v0.6)
python -m casa.cli bench_schema_predict \
  --store-dir lab/agent-stores/math-l0-lab \
  --bundle lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json \
  --cues lab/exp_l/schema_predict_cues.v1.json

# Persist F0 on field_state (optional)
python -m casa.cli f0_math_ingest --store-dir lab/agent-stores/math-l0-lab \
  --bundle lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json --boot-ltm-only --write
```

См. `design/f0-math-logical-layer.md`, `design/understanding-contract.md` (UC v0.1: `claims_nav_enabled` в `cen_plan`).

## Exp T9 / Predictor smoke (UC v0.5)

```bash
# Segment predict + critic (field intuition)
python tools/bench_predict.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --cues lab/exp_t9/segment_predict_cues.v1.json

# T9 prefix disambiguation on L2 lexicon
python tools/bench_t9_predict.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --cues lab/exp_t9/t9_prefix_cues.v1.json

# Letter-by-letter T9 tick loop (UC v0.6)
python tools/bench_predict_tick.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --cues lab/exp_t9/t9_tick_cues.v1.json

# Manual anchor cues + lexicon sweep (optional)
python tools/bench_t9_lexicon_sweep.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --manual-cues lab/exp_t9/t9_manual_cues.v1.json \
  --sample 200

# Lexicon miss → cold ingest → predict again (offline headwords v0)
python tools/bench_lexicon_cold.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --cues lab/exp_t9/lexicon_cold_cues.v1.json \
  --headwords lab/exp_t9/lexicon_cold_headwords.v1.txt

# NCA stale shards: cold ingest queues pending → dry-run detect (no CUDA train)
python tools/bench_nca_stale.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --headwords lab/exp_t9/lexicon_cold_headwords.v1.txt \
  --min-tokens 1

# Incremental sleep repair: train only stale L2 shards (default 25 epochs)
python tools/nca_stale_shards.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --sync-registry --dry-run

# VK layouts on field (L0_vk_map core ltm)
python tools/vk_layout_ingest.py
python tools/bench_vk_layout_field.py
python tools/bench_layout_parity.py
dotnet test apps/Casa.Act.Core.Tests
```

См. `design/predictor.md`, `design/experiment-t9-predictive-words.md`.

## Exp bilingual v0 (EN + entity hub)

Separate stores: **RU** `sss-ru-lexicon`, **EN folk** `sss-en-folk` (Grimm + Jacobs, full headword list including articles).

```bash
# 1. Create EN folk store (~6700 headwords, batch L2, no stopword filter)
python tools/init_en_folk_store.py \
  --headwords lab/exp_bilingual/en_folk_headwords.v1.txt

# 2. Linked boot + entity hub (L3 only; L2 stays on each store)
python tools/bench_bilingual_linked.py \
  --ru-store lab/agent-stores/sss-ru-lexicon \
  --en-store lab/agent-stores/sss-en-folk \
  --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json

python tools/bench_grapheme_clusters.py \
  --cues lab/exp_bilingual/grapheme_cluster_cues.v1.json
```

Dev overlay on RU store (legacy lab):

```bash
# See lab/exp_bilingual/README.md
python tools/bench_entity_hub.py \
  --store-dir lab/agent-stores/sss-ru-lexicon \
  --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json
```

Regenerate map: `python tools/memory_manifest.py --store-dir <path> --write`

## Agent profiles

Один CASA core, разные продукты = **exported agent store** (`ltm/` + `nca/`) + **profile JSON**.

| Doc | Роль |
|-----|------|
| [`design/CASA-ADR-0007-agent-profile-store-packs.md`](../../design/CASA-ADR-0007-agent-profile-store-packs.md) | канон |
| [`lab/agent-profiles/`](../agent-profiles/) | `bilingual-t9-console`, `dev-ide-complete` |

```bash
# Export перед поставкой (канон)
python tools/export_ltm_pack.py --store-dir lab/agent-stores/sss-ru-lexicon
python tools/export_ltm_pack.py --store-dir lab/agent-stores/sss-en-folk
```

Planned: `run_agent_profile.py`
