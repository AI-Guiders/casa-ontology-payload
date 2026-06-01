# Memory hierarchy (agent store) — KB-like index

**Status:** v0 (`memory_manifest.py`)  
**Date:** 2026-05-30  
**See:** [`l2-lattice-sharding.md`](l2-lattice-sharding.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0017-compact-persist.md`](CASA-ADR-0017-compact-persist.md), [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) (опыт без картридж-продукта; transfer matrix), [`CASA-ADR-0022-agent-v1-existence-bar.md`](CASA-ADR-0022-agent-v1-existence-bar.md) (бар «живого агента» v1, не AGI), [`CASA-ADR-0023-sleep-scale-thin-first.md`](CASA-ADR-0023-sleep-scale-thin-first.md) (batched sleep, thin-first, ingest hippo), [`prism-memory-architecture-v1.md`](prism-memory-architecture-v1.md) (KB L0–L3 parity для `field_state.prisms`)

## Tree (analog of KB folders)

```text
agent-store/{id}/              # e.g. lexicon-ru-archaic (not corpus name)
├── MEMORY.md                 ← human map (generated)
├── memory_manifest.json      ← machine map (generated)
├── field_state.json          ← **runtime checkpoint** (prism_hippo queue, SN meta; not in profile tar)
├── agent_session.json        ← runtime checkpoint (FPN WM)
├── ltm/                      ← **shipped** memory structure (vocab + placements)
│   ├── pack.manifest.json
│   └── l2/L2_word_07.ltm
├── nca/                      ← **shipped** NCA registry (same weights; not in cartridges)
│   ├── L1_syllable/model.pt
│   ├── L2_word_07/model.pt
│   └── train_shards_report.json
├── ingest_log.ndjson         ← optional: corpus sources (Afan, bukvar, …)
├── journal/                  ← agent-owned prose (NOT in ltm/ export)
│   ├── index.json
│   └── {scope}/entries.jsonl   ← FS shard = optional scope label (default `self`)
│       # tags/meta.notebook — agent collections (Zettelkasten, drafts, …)
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
| **Shipped** | память агента | `ltm/`, `nca/` | **да** — все content-призмы + NCA paths | **да** (ops tar) | `compact_persist_store` / `export_ltm_pack` |
| **Runtime** | checkpoint | `field_state.json` (thin_v1 + ltm/), `agent_session.json` | **нет** — hippo в thin JSON; cells из `ltm/` | **нет** | `save_runtime_state` (thin → sync `ltm/` + overlay) |
| **Self** | agent-owned | `agent/`, `journal/` | load если каталог есть | **нет** (opt-in backup) | `save_agent_prism`, journal CLI |

```text
  Shipped (ltm/ + nca/)     ──cold boot──►  структура prism_memory + NCA paths (+ control)
         ▲                                      │
         │ compact_persist / export_ltm_pack    │ T_wake: append_episode
         │                                      ▼
  Runtime checkpoint          ◄──save_runtime_state──  зеркало структуры + prism_hippo queue
  (field_state, session)                         (не «место знания», а checkpoint)

  Self (agent/, journal/)     ◄── agent_remember ──  не в ltm/ без agent_promote
```

**Hippo:** wake пишет в **runtime checkpoint**; после **sleep** консолидация уходит в **структуру памяти** (`prism_memory` → `ltm/`); episodic queue **prune** — не дублировать в profile tar как dump эпизодов. На больших store: **thin checkpoint до sleep**, батчи consolidate — [`CASA-ADR-0023-sleep-scale-thin-first.md`](CASA-ADR-0023-sleep-scale-thin-first.md).

**Код:** константы `STORE_TIER_*` в `casa/prisms/shared/store_layout.py`; flush — `casa/prisms/shared/store_persist.py`.

**Неявная vs явная память:** [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md) § Неявная vs явная — tick/hippo/структура памяти vs `agent_remember`.

### Фактология vs картриджи (canon)

Продуктовая модель «только опыт, без картриджей» — [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md). **Shipped tier** здесь = **agent memory pack** (`ltm/` + `nca/`), не ingest cartridge.

Всё **фактическое**, чем агент оперирует, — в **его структуре памяти** (`prism_memory`: раскладка на решётках → `ltm/` после sleep; runtime-зеркало — `field_state.json`) и в **self** (`agent/`, `journal/`). **Не** в ingest-картриджах (`bundles/`, corpus, lab KB JSON) и **не** как runtime-oracle из них.

**NCA** (`model.pt` на решётку): веса **те же** — при «переезде» меняется только **реестр в памяти агента** (`{store}/nca/`, shipped tier). NCA **не** лежат в картриджах; картридж лишь **запускает** ingest/train, итог — память (`ltm/` + `nca/`).

| Что | В памяти агента | Ingest / картридж (только источник) |
|-----|-----------------|-------------------------------------|
| Headwords (DetCorpus, Afan) | L2 `lang.word.*` в `ltm/` | `headwords.v1.txt`, listen encode |
| Alphabet / bukvar | L0–L1 в `ltm/` | `kb-bukvar-*.json` — **ingest-only** |
| NCA repair | `nca/<lattice>/model.pt` | train offline; **не** bundle |
| Частота / era / T9 filter | L3 `usage_axis` edges | `lexicon_axes.jsonl` — audit + cold rebuild |
| Math frames / ops | F0 `frame` + `denotes` | `kb-math-*.json` — ingest-only |
| Teacher episodes | hippo → sleep → `ltm/` | не bundle links at predict |

`bundles/` в store — снимок ingest и SN/CEN bootstrap; **predict/read path не открывает** её как справочник ответов.
### Черновики и эксперименты (Self journal, не отдельный tier)

Черновики — **записи в `journal/`** с `tags: ["draft"]`, опционально `meta.notebook` / `notebook:*` tag, `meta.status`, `meta.links` (Zettelkasten). Сколько «тетрадей» — решает агент.

| kind | role |
|------|------|
| `hypothesis` / `experiment` | «кажется, step 2 → mul» + `test_cues` |
| `question` | открытый вопрос |
| `note` / `draft` | наблюдение без проверки |

`meta.status`: `open` → `testing` → `confirmed` / `rejected` / `unclear`. **`workbook_check`** гоняет predict по `test_cues`. **`agent_promote`** — явный перенос confirmed (или `--allow-unconfirmed`) → hippo episode + sleep → `ltm/` (структура памяти). Код: `agent_workbook.py`, `agent_promote.py`, CLI `agent_workbook`, `agent_promote`.

## Prism layers (KB parity)

Операционные слои **P0–P3** (hot / operational / episodic / router) для `field_state.prisms` — тот же контракт, что KB **L0–L3** для agent-notes: budgets, compaction, maintenance, retrieval order. Полная таблица и правила: [`prism-memory-architecture-v1.md`](prism-memory-architecture-v1.md); manifest: [`prism-memory-architecture-v1.json`](prism-memory-architecture-v1.json).

| KB | CASA prism |
|----|------------|
| L0 hot | `prism_hot_context` + SN meta |
| L1 operational | content + `prism_control` |
| L2 archive | `prism_hippo`, `journal/` |
| L3 routing | `prism_router` |

## Logical hierarchy

```text
cylinders
├── prism_memory (lexicon)     ← структура памяти; NCA paths → {store}/nca/ (не картридж)
│   ├── L0_grapheme          [1 lattice → 1 NCA]│   ├── L1_syllable          [1 lattice, 1 NCA]
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
python tools/memory_manifest.py --store-dir lab/agent-stores/lexicon-ru-archaic --write
```
