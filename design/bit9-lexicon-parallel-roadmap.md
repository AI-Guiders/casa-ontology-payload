# BiT9 now · lexicon enrichment in parallel (v0)

**Date:** 2026-05-30  
**Status:** plan + lab gate  
**Related:** ADR-0006, ADR-0007, ADR-0008, `lexicon-corpus-quad.md`, [`casa-wake-sleep-concept.md`](casa-wake-sleep-concept.md)

## Принцип

| Трек | Когда | Цель |
|------|--------|------|
| **A — BiT9 technical** | **сейчас** | linked RU+EN predict, homoglyph, hub — benches green, console demo |
| **B — Product act** | позже | Native AOT IPC, preview chip, layout-parity profile |
| **C — Lexicon mass** | **фон, автономно** | полные словари → поле → сущности/POS/роли → рёбра → explain |
| **D — GPU** | на каждом batch/sleep | NCA train/repair **CUDA** (`train_memory_nca_shards`, `nca_stale_shards`) |

Треки **C** и **A** не блокируют друг друга.

---

## A. BiT9 — проверка сейчас (gate)

```bash
python tools/bench_bilingual_linked.py \
  --ru-store lab/agent-stores/lexicon-ru-general \
  --en-store lab/agent-stores/lexicon-en-folk \
  --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json

.\scripts\run_bit9_gate.ps1          # smoke + T9 sweep 1000×RU + 1000×EN
.\scripts\run_bit9_gate.ps1 -SmokeOnly   # integration + merged preview cues

python tools/bench_t9_lexicon_sweep.py \
  --store-dir lab/agent-stores/lexicon-ru-general --sample 1000 --t9-policy lab \
  --min-full-rate 0.99 --min-prefix-rate 0.15 \
  --out lab/exp_bilingual/reports/bit9_ru_sweep_1000.json
```

**Критерий «технически ок»:** linked L2+T9+hub+cross green; unified 3/3; RU boot `ltm_only` + EN field/ltm.

**Не входит в A:** layout-parity act, полный ru-general корпус, prod tar.

---

## C. Lexicon mass — фоновый конвейер

### C0. Источники (не Афан = весь RU)

| Corpus ID | Назначение | Источник (кандидаты) | Лицензия / примечание |
|-----------|------------|----------------------|------------------------|
| `ru-general` | бытовой RU | **DetCorpus 50k** (CC0), `fetch_ru_frequency_headwords.py` | канон 2026-05-30 |
| `ru-literary` | книжный слой | Afan 624 txt (уже есть) | in-repo |
| `ru-tech` | IDE/KB | scan + seed | in-repo |
| `en-general` | EN | **OpenSubtitles 50k** (MIT), `fetch_en_frequency_headwords.py` | hermitdave/FrequencyWords |
| `en-tech` | EN commands | scan + seed | in-repo |

Headwords: `casa-lexicon-build quad` (Native AOT) или внешний `.txt` → `init_lexicon_store.py`.

### C1. Поле (batch, один раз на снимок)

1. `init_lexicon_store.py --corpus-id <id>`
2. `remigrate_l2_lex.py` — **один раз** на store при новом базовом списке
3. **`train_memory_nca_shards.py --device cuda`** — все L2 shards + L1
4. `export_ltm_pack.py` + `memory_manifest.py --write`

### C2. Сущности, POS, роли (после L2 есть слова)

Порядок слоёв (параллельно по store, не смешивая hot path):

```text
  L2 lang.word.*     (уже)
       ↓
  L3 entity.*        entity_hub_ingest + KB bundles
       ↓
  tags / forms       ADR-0003 emergent tags (не сверху в v0)
       ↓
  edges              E:denotes, compose, role.* (KB graph patch)
       ↓
  explain            articulation / KB claims (offline, sleep)
```

Инструменты уже в lab: `entity_hub_ingest`, `f0_math_ingest` (schema), bundles в `lab/kb/`.

POS/роли v0: **не новый organ** — claims + edges на L3/L2, ingest из внешнего лексикона (OpenCorpora morph → bundle), не LLM на hot path.

### C3. Автономный цикл (sleep)

```bash
python tools/agent_autonomous_tick.py \
  --store-dir lab/agent-stores/lexicon-ru-general \
  --cues lab/exp_t9/lexicon_cold_cues.v1.json \
  --headwords <miss-list.txt> \
  --train-nca --device cuda

python tools/nca_stale_shards.py \
  --store-dir <store> --train --device cuda --sync-registry
```

Wake: predict + detect miss → cold ingest.  
Sleep: stale shards → **CUDA** NCA только для изменённых полок.

### C4. GPU (обязательно)

| Шаг | Команда | device |
|-----|---------|--------|
| Full shard train | `train_memory_nca_shards.py --layer all` | `cuda` |
| Incremental | `nca_stale_shards.py --train` | `cuda` (default) |
| VK repair | `vk_nca_train.py` | `cuda` |
| Autonomous tick | `agent_autonomous_tick.py --train-nca` | `cuda` |

Перед пересборкой exe: `debug_stop` если netcoredbg держит PDB (правило workspace).

---

## B. Product (позже)

- Profile export + boot без `field_state` в tar
- C# act вместо Python serve
- ADR-0008 physical keys + preview

---

## Чеклист исполнения

- [x] BiT9 linked bench green (2026-05-30)
- [x] unified + ambiguous benches — `scripts/run_bit9_gate.ps1` on `lexicon-ru-general` (2026-05-30)
- [x] ru-general headwords **вне Афан** + init store
- [ ] quad stores OR обновить prod RU store с новым списком
- [x] GPU NCA ru-general — migrate v1 ids + 64 shards CUDA, stale 0 (2026-05-31)
- [ ] GPU NCA на остальных stores (en-folk уже есть; quad TBD)
- [x] entity/POS/taxonomy bundles + sleep ingest — `run_sleep_semantic_ingest.ps1`, UD POS 3790+ claims (2026-05-31)
- [x] parallel tracks gate — `run_bit9_parallel_tracks.ps1` (A scale + C2 POS/taxonomy + semantic prior bench)
- [ ] `run_agent_profile` + prod pack
