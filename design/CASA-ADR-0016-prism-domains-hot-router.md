# CASA-ADR-0016: доменные призмы, hot-context и router

**Статус:** принято (design + API v0, 2026-06-01)  
**Область:** `field_state.prisms`, predict/sleep, store layout  
**Связано:** [`memory-hierarchy.md`](memory-hierarchy.md), [`prism-memory-architecture-v1.md`](prism-memory-architecture-v1.md) (KB L0–L3 parity, compaction, maintenance), [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`context-axis.md`](context-axis.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md)

---

## Решение (одной фразой)

**Память агента** — дерево **призм** (домен / hot-context / router); **решётки** — области внутри content-призмы. Агент и sleep **могут создавать** новые призмы и решётки; ingest-картриджи только **заполняют** content, не подменяют router/hot.

---

## Иерархия

```text
agent store (структура памяти)
└── prisms.{prism_id}
    ├── kind: content | hot_context | router
    ├── stack → design/prisms/<genre>/stack.json
    └── lattices{…}          # только у content (и опц. agent-owned)
        └── cells / tokens

prism_hot_context            # edges only — без ltm/NCA encyclopedia
prism_router                 # routes only — опционально в profile
prism_memory                 # legacy default content (RU+math monolith v0)
prism_lang_ru                # целевая content-призма (roadmap / spawn)
prism_math                   # F0 / schema
prism_hippo                  # episodic (как было)
prism_control                # CU (как было)
```

| Уровень | Что хранит | Shipped `ltm/` + `nca/` | Пример |
|---------|------------|-------------------------|--------|
| **Router** | правила `match → target_prism` | нет (малый JSON в checkpoint) | `t9+ru → prism_lang_ru` |
| **Hot-context** | рёбра `src–rel–dst`, salience, TTL | promote только подтверждённые | `cue:дом → lang.word.дом` |
| **Content** | токены на решётках | **да** | `lexicon` shards, `schema-math` |
| **Lattice** | область в призме | shard `.ltm` + `model.pt` | `L2_word_07`, `memory.phrase` |

**Не путать:** `prism_control` — процедура SN/CEN/FPN; **router** — декларативная память «куда идти за фактами».

---

## Три kind призм

### 1. `content` (домен)

- Полные решётки, z_bridges внутри призмы, NCA repair.
- Сложные домены — **отдельные** `prism_id` (`prism_lang_ru`, `prism_math`, позже `prism_syntax_ru`).
- **Синтаксис:** сначала решётка в `prism_lang_*`; отдельная призма — когда свой stack + Extract + мосты.

### 2. `hot_context` (только связи)

- **Не** дублирует L2 headwords.
- Рабочий граф на тик/сессию: disambiguation, entity frame, «сейчас в фокусе», мост к episodic id.
- **Aggressive prune**; в shipped — только после `agent_promote` / sleep gate (как journal → profile).
- Predict: сначала hot edges (узкий граф), затем content по router.

### 3. `router` (маршрутизатор)

- Таблица маршрутов: `{modality, locale, segment, tier, …} → prism_id [, lattice_hint]`.
- **Опционально:** один домен в profile → `default_content_prism` без отдельного spawn.
- Может **расти** из опыта (emergent route) с Critic gate — v1+.

---

## Tick (порядок)

```text
INPUT
  → resolve_route(state, ctx)     # prism_router
  → merge_hot_context_digest()    # prism_hot_context edges
  → predict on content_prism      # lattices + NCA paths
  → surprise → prism_hippo
  → sleep → strengthen content + promote edges (gate)
```

`sn.active_prism` после resolve указывает **content**-призму, не router/hot.

---

## API v0 (код)

| Функция | Модуль |
|---------|--------|
| `spawn_prism(state, prism_id, kind=…)` | `casa.prisms.memory.prism_spawn` |
| `spawn_content_lattice(state, prism_id, lattice_id, …)` | там же |
| `add_hot_edge` / `hot_edges` / `prune_hot_context` | `casa.prisms.memory.prism_hot_context` |
| `add_route` / `resolve_route` | `casa.prisms.memory.prism_router` |
| `content_prism_lattices(state, prism_id=…)` | `casa.prisms.memory.memory_prisms` |

Константы: `PRISM_HOT_CONTEXT`, `PRISM_ROUTER` в `prism_state.py`.

---

## Store на диске (roadmap)

```text
{store}/
  ltm/memory/lexicon/…       # content prism_lang_ru
  ltm/memory/math/…
  ltm/meta/hot_context.jsonl # опц. audit
  ltm/meta/router.json
  nca/memory/lexicon/…
```

v0: content остаётся в `prism_memory` + legacy `ltm/l2/`; spawn новых content-призм пишет в `field_state` only. Subdirs `ltm/memory/` — S5 в [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md).

---

## Миграция

| Было | Стало |
|------|--------|
| один `prism_memory` на всё | default content; spawn `prism_lang_ru` по мере split |
| SN только heuristic | + `resolve_route` при наличии `prism_router` |
| L3 oracle + entity hub | ситуативное → `prism_hot_context` |

Без breaking: `memory_lattices(state)` без аргумента = `prism_memory`.

---

## Non-goals (v0)

- Полный split `lexicon-ru-general` store на несколько content-призм на диске.
- Emergent router training без gate.
- Hot-context как отдельный NCA stack (edges only).

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR + API v0 (`prism_spawn`, hot_context, router) |
| 2026-06-01 | bootstrap routes on `ensure_prisms`; profile `default_content_prism`; T9 hot salience re-rank |
