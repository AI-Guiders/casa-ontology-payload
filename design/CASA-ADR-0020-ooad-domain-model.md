# CASA-ADR-0020: OOA&D domain model (код ↔ design SSOT)

**Статус:** принято (design + v0 code `casa/domain/`)  
**Дата:** 2026-06-01  
**Область:** рефакторинг к объектной модели поверх `field_state` dict  
**Связано:** [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`CASA-ADR-0016`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0035-multi-layer-routing.md`](CASA-ADR-0035-multi-layer-routing.md), [`prism-memory-architecture-v1.json`](prism-memory-architecture-v1.json), stack JSON в `design/prisms/`

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

Route / RouteContext / RouteTarget / RoutingChain / PlanTick
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
| `casa.domain.routing` | `Router`, `Route`, `RouteContext`, `RouteTarget`, `RoutingChain` (`route_kind`: knowledge / capability / goal / applicability — ADR-0035) |
| `casa.domain.plan_tick` | `PlanTick`, `promote_*_route` (emergent after gate) |
| `casa.domain.emergent_promote` | `promote_from_probe_report`, `suggest_trial_plan`, Critic dedup |
| `casa.domain.kolb_cycle` | `KolbPhase`, `maybe_kolb_revise_tick` — META; домены в `kolb_handlers` |
| `casa.domain.pdca_cycle` | `PdcaPhase`, `infer_pdca_phase` — META; оболочка tick 1–5 |
| `casa.prisms.tick.pdca_act_tick` | `maybe_pdca_act_tick` — централизованный Act после Check |
| `casa.prisms.tick.pdca_check_tick` | `maybe_pdca_check_tick` — Check: hippo, goal, metacog |
| `casa.domain.spacing_policy` | retrieval schedule → rehearsal goal |
| `casa.domain.goal_emergent` | goal из surprise |
| `casa.domain.metacog_gate` | tract readiness pre-check |
| `casa.domain.scaffold` | ZPD scaffold levels |
| `casa.prisms.hippo.kolb_cycle` | batch Kolb (`kolb_count_row`) |
| `casa.domain.knowledge_tracing` | `p_known`, retrieval interval |
| `casa.domain.mastery_gate` | CBE streak before promote |
| `casa.domain.deliberate_practice` | `weakest_link`, JIT focus |
| `casa.domain.progression_ring` | spiral L0→L4 goals |
| `casa.domain.scaffold_fading` | ZPD scaffold level in state |
| `casa.domain.goal_arbiter` | единый арбитр намерения Plan/Check |
| `casa.domain.hypothesis_queue` | гипотезы expect→verify |
| `casa.domain.self_model` | tract confidence из gate |
| `casa.domain.intent_checkpoint` | WM после прерывания |
| `casa.domain.load_governor` | cognitive load policy |
| `casa.domain.edge_relink` | `agent_relink_crosslink`, `relink_vis_lex_bridge`, `supersede_emergent_route` (Kolb AE) |
| `casa.prisms.tick.agent_self_drive_tick` | `seek_agent_knowledge`, `maybe_promote_skill_on_verify` (conscious life) |
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
| 2026-06-05 | `route_kind`, `RoutingChain`, `PlanTick`; `prism_router.tick_prepare_memory` → vertical resolve (ADR-0035) |
