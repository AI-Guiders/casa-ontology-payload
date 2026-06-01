# Prism memory architecture v1 — KB parity (layered)

**Status:** canon (design); code v0 partial (hot T9 re-rank + route bootstrap on ensure)  
**Date:** 2026-06-01  
**KB canon:** `knowledge/work/projects/door-to-singularity/ca-substrate-agent/kb-casa-prism-memory-architecture-v1.md` (agent-notes MCP). **Lab projection:** этот файл + JSON manifest.  
**See:** KB `META/memory-architecture-layered-extended-v1.md`, [`memory-hierarchy.md`](memory-hierarchy.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md)

Проекция **того же контракта**, что KB v1 (L0–L3, budgets, compaction, maintenance), на **`field_state.prisms`** и store tiers. Не дублирует ingest/ltm-pack — см. [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md).

**Manifest (machine):** [`prism-memory-architecture-v1.json`](prism-memory-architecture-v1.json)

---

## Parity map (KB ↔ CASA prism)

| KB layer | Роль в сессии агента (notes) | CASA prism / tier | Always load? |
|----------|------------------------------|-------------------|--------------|
| **L0** Hot | goal, blockers, guardrails | `prism_hot_context` + SN meta (`active_prism`, `active_lattice`, mode) | **да** на каждый tick |
| **L1** Operational | scope slice, execution gate | **content** призма в фокусе + `prism_control` (CU) | да в wake; lattice subset |
| **L2** Episodic archive | revisions, history on demand | `prism_hippo` + `journal/` (Self) | **нет** — query / sleep / promote |
| **L3** Semantic routing | facets, retrieval order | `prism_router` | resolve first; не гидратировать все content |

**Инвариант (как в KB):** split по призмам/scope **улучшает** операции, но **не заменяет** маршрутизацию (`prism_router` → content) и **не** подменяет shipped факты (`ltm/`).

**Не путать с решётками L0–L3 в `prism_memory`:** там **z-уровни** лексикона (grapheme→phrase). Здесь **P0–P3** — операционные слои **контура памяти**, по аналогии с KB L0–L3.

---

## P0: Hot state (`prism_hot_context`)

**Source of truth:** `field_state.prisms.prism_hot_context` (runtime checkpoint; опц. audit `ltm/meta/hot_context.jsonl`).

**Содержимое:** только **рёбра** `src – relation – dst` (salience, ttl_ticks, provenance). **Не** headwords, **не** NCA.

**Always load на tick:** digest соседей для cue (`hot_digest_for_cue`) — узкий граф, не полный L2.

**Compatibility mirror (аналог L0 stubs в KB):**

| Поле / API | Роль |
|------------|------|
| `sn.active_prism` | content-призма после `resolve_route` |
| `sn.active_lattice` | решётка в фокусе |
| `sn.mode` | `wake` \| `sleep` |
| `hot_edges` / `add_hot_edge` | рабочий граф |
| `prune_hot_context` | compaction P0 |

**Бюджеты (v0):**

| Порог | Значение | Действие |
|-------|----------|----------|
| soft | `len(edges) > 1024` | warning в отчёте tick; рекомендовать `prune_hot_context` |
| hard | `len(edges) > max_edges` (default 4096) | auto-prune перед add; **не** расширять shipped |

**Writing contract (как `hot-context-writing-contract` в KB):**

- Писать только **decision-grade** связи: disambiguation, entity frame, «сейчас в фокусе», мост cue→concept id.
- **Не** дублировать факты, уже на content-решётке (нет `lang.word.*` «на всякий случай»).
- `provenance`: `tick` \| `agent_remember` \| `sleep_promote` \| `bootstrap`.
- Dedupe по `(src, relation, dst)` — bump salience, не плодить копии.

---

## P1: Operational memory (content + control)

**Content:** `prism_*` с `kind=content` (`prism_memory`, `prism_lang_ru`, `prism_math`, …) — решётки + NCA paths.

**Control:** `prism_control` — не «память фактов», но **всегда** в wake-контуре (SN/CEN/FPN, predict gate).

**Правило загрузки (аналог L1 scope slices):**

- На tick читать **одну** content-призму (`sn.active_prism`) + lattices по router hint.
- **Не** гидратировать все content-призмы в predict (как KB: не тащить все `scope-*` в hot).

**Operational triggers:**

| Когда | Действие |
|-------|----------|
| Смена locale/modality/segment | `resolve_route` → обновить `active_prism` |
| Новая content-призма по задаче | `spawn_prism` + `spawn_content_lattice` |
| После sleep | перечитать shipped `ltm/` в структуру призмы |

---

## P2: Episodic archive (`prism_hippo` + Self)

**Hippo:** быстрая запись на T_wake; consolidate на T_sleep → **content** (`prism_memory` / domain prism).

**Journal (Self tier):** prose, drafts, hypotheses — **не** в profile tar; promote → hippo → sleep → `ltm/` только через `agent_promote`.

**Правило (как L2 archive в KB):**

- Episodic queue **не** сериализовать в shipped dump эпизодов.
- Историю эпизодов подгружать **явно** (replay cue, sleep report, audit) — не по умолчанию в каждый predict.

**Compaction:**

- После успешной consolidate — **trim** hippo (TTL / cap episodes).
- Journal: ротация по scope — см. [`CASA-ADR-0013-agent-journal.md`](CASA-ADR-0013-agent-journal.md).

---

## P3: Semantic routing (`prism_router`)

**Аналог L3:** не жёсткий домен, а **таблица маршрутов** `{modality, locale, segment, tier, …} → prism_id [, lattice_hint]`.

**Retrieval order contract (CASA tick):**

```text
resolve_route(state, ctx)
  → merge_hot_context_digest(cue)     # P0 hints only
  → predict on content_prism          # P1
  → surprise → prism_hippo            # P2 write
  → sleep → consolidate + promote     # P2→shipped
```

**Правило:** router грузит **только** top match; **не** обход всех `prisms.*` с `kind=content`.

**On-demand (не в каждый tick):**

- Полный список маршрутов — debug / `memory_manifest` / spawn CLI.
- Emergent routes (v1+) — только с Critic gate (ADR-0016 non-goals v0).

---

## Store tiers × layers (сводка)

См. [`memory-hierarchy.md`](memory-hierarchy.md) § Store tiers. Слои P0–P3 **накладываются** на tiers:

| Tier | P0 | P1 | P2 | P3 |
|------|----|----|----|-----|
| **Shipped** (`ltm/`, `nca/`) | — | content cells + NCA | — | опц. `ltm/meta/router.json` |
| **Runtime** (`field_state.json`) | hot edges | prism mirrors + hippo queue | episodic queue | routes |
| **Self** (`agent/`, `journal/`) | — | agent lattices | journal prose | — |

**Flush:**

| Событие | Что уходит в shipped |
|---------|----------------------|
| `compact_persist_store` / `export_ltm_pack` | all content prisms → `ltm/`, NCA paths, router meta |
| `save_runtime_state` | P0+P1+P2+P3 checkpoint (не dump всех эпизодов в tar) |
| `agent_promote` | подтверждённые hot edges → hippo → sleep → ltm (gate) |

---

## Compaction loop (аналог `memory-compaction-loop-v1`)

**Порядок при давлении на runtime (как `compact_order_suffix` в KB):**

1. `prune_hot_context` — P0, агрессивно (низкая salience, истёкший ttl).
2. Trim `prism_hippo` — после consolidate или cap по эпизодам.
3. **Не** compact shipped `ltm/` без явного rebuild/migrate.
4. Journal — вне tick hot path; архив по политике ADR-0013.

**`prism_memory_health` (операционный аналог `memory_health`):**

Запускать:

- перед длинной серией wake-тиков / curriculum;
- после bulk ingest в store;
- после восстановления из `field_state` checkpoint;
- когда tick report: `hot_edges` > soft budget.

**Проверки v0:**

| Check | Fail если |
|-------|-----------|
| router resolves | `active_prism` content существует |
| hot budget | edges > hard max |
| hippo cap | queue > policy (post-sleep) |
| nca.models | lattice без path для active content |
| kind integrity | `hot_context` без lattices; `content` без kind |

**CLI / код:** `python -m casa.prisms.memory.prism_memory_health` or `tools/prism_memory_health.py`; v0 — `prune_hot_context` + `run_prism_memory_health`.

---

## Large structure policy (аналог `memory-large-sections-policy-v1`)

| Артефакт | Политика |
|----------|----------|
| `field_state.json` с полными cells | **антипаттерн** для shipped; checkpoint OK |
| L2 shard `.ltm` | один shard — один NCA; не monolith L2 |
| hot edges | cap + salience decay |
| router table | O(routes) малый; не дублировать KB |

---

## Maintenance rules

1. **Новый kind призмы** — ADR + `design/prisms/<genre>/stack.json` + константа в `prism_state.py`.
2. **Новый content domain** — `spawn_prism` + subdir `ltm/memory/<domain>/` (S5 layout), не новый store id без причины.
3. **Правки канона KB** — только agent-notes MCP; этот файл — **проекция** для lab (как [`lattice-naming-v1.md`](lattice-naming-v1.md)).
4. **При добавлении P-layer политики** — обновить JSON manifest, KB `kb-casa-prism-memory-architecture-v1.md`, § parity в [`memory-hierarchy.md`](memory-hierarchy.md).
5. **Breaking rename `prism_*`** — migrate script + alias в `normalize_prisms`; не ломать cold boot.

---

## API map (v0)

| KB tool (notes MCP) | CASA v0 |
|---------------------|---------|
| `memory_health` | `run_prism_memory_health` / `tools/prism_memory_health.py` |
| `compact_hot_context` | `prune_hot_context(state, max_edges=…)` |
| `route_context` | `resolve_route` + `apply_route_to_sn` |
| `read_hot_context` | `hot_edges` / `hot_digest_for_cue` |

| Функция | Модуль |
|---------|--------|
| `spawn_prism`, `spawn_content_lattice` | `prism_spawn.py` |
| `add_hot_edge`, `prune_hot_context`, `hot_digest_for_cue` | `prism_hot_context.py` |
| `add_route`, `resolve_route`, `apply_route_to_sn` | `prism_router.py` |
| `ensure_prisms`, `content_prism_lattices` | `memory_prisms.py` |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | v1: KB parity doc + manifest (после ADR-0016) |
