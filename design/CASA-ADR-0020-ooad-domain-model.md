# CASA-ADR-0020: OOA&D domain model (код ↔ design SSOT)

**Статус:** принято (design + v0 code `casa/domain/`)  
**Дата:** 2026-06-01  
**Область:** рефакторинг к объектной модели поверх `field_state` dict  
**Связано:** [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`CASA-ADR-0016`](CASA-ADR-0016-prism-domains-hot-router.md), [`prism-memory-architecture-v1.json`](prism-memory-architecture-v1.json), stack JSON в `design/prisms/`

---

## Зачем

Design уже задаёт **агрегаты и роли** (призмы, решётки, router, tiers P0–P3). Код v0 — **процедуры над `dict`**, дублирующие имена полей. OOA&D слой:

- **один** объектный словарь терминов;
- **граница persistence**: `FieldState.from_dict` / `to_dict`;
- **сервисы** (spawn, route, compact) принимают домен, не «магические» ключи.

**Не big-bang:** strangler — старые `prism_router.resolve_route(state, …)` делегируют в domain; `state` dict остаётся wire format checkpoint/ltm.

---

## Анализ (объекты из модели)

```text
AgentStore (корень на диске)
└── FieldState                    ← aggregate root (checkpoint)
    ├── schema_version, field_version
    ├── SessionFocus (sn)         ← active_prism, active_control_prism, mode
    ├── PrismCatalog              ← dict prism_id → Prism*
    │   ├── ContentPrism          ← lattices: Lattice*
    │   ├── ControlPrism          ← lattices (CU) | monolith prism_control
    │   ├── HotContextPrism       ← edges: HotEdge*
    │   ├── RouterPrism           ← routes: Route*
    │   └── HippoPrism            ← episodes (отдельный модуль позже)
    ├── L2ShardingPlan            ← word_index (memory domain)
    └── VisRefIndex               ← image_ref → vis.concept_id

StackSpec (read-only SSOT)        ← design/prisms/*/stack.json
└── LatticeSpec[]

Lattice                           ← value object
└── Grid (cells[][] tokens)

Route / RouteContext / RouteTarget
```

**Инвариант:** `StackSpec` не живёт в runtime — только bootstrap/spawn читает JSON.

---

## Design (пакеты)

| Пакет | Ответственность |
|-------|----------------|
| `casa.domain.lattice` | `Lattice`, `Grid`, token helpers |
| `casa.domain.prism` | `Prism`, `ContentPrism`, `HotContextPrism`, `RouterPrism`, `ControlPrism`, factory |
| `casa.domain.field_state` | `FieldState`, `SessionFocus`, `PrismCatalog` |
| `casa.domain.stack` | `StackSpec`, `load_stack` |
| `casa.domain.routing` | `Router`, `Route`, `RouteContext`, `RouteTarget` |
| `casa.domain.persistence` | `field_state_from_dict`, `field_state_to_dict` |

**Application services** (постепенно): `casa.prisms.*` вызывают domain; не наоборот.

---

## Миграция кода (strangler)

| Фаза | Модули | Статус |
|------|--------|--------|
| M0 | `casa/domain/*`, тест round-trip | **done** |
| M1 | `prism_router` → `domain.routing.Router` | **done** |
| M2 | `prism_spawn`, `export_ltm_pack` | roadmap |
| M3 | `compact_persist`, `ingest_vis`, tick | roadmap |
| M4 | убрать прямой доступ к `state["prisms"]` вне persistence | roadmap |

**Wire format не меняется:** `multi_prism_v1` JSON как был.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0020 + `casa/domain` v0, router delegate |
