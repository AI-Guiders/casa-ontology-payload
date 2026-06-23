# ADR-0085: Concept Zone — Built-In vs Self-Earned theories, supersede bootstrap

**Status:** proposed (draft)  
**Date:** 2026-06-22  
**Provenance:** оператор (Света) + агент — после разбора ConceptNet Димы, P18 stub (4 hub), и требования: полноценные concept cells + агент может исправить ошибку в Built-In  
**Supersedes / amends:** [CASA-ADR-0073](CASA-ADR-0073-concept-layer-lexicalization.md) §3 rollout target; [CASA-ADR-0083](CASA-ADR-0083-curriculum-ontology-agent-store.md) §7 (Concept Zone shelf vs catalog)  
**Related:** [CASA-ADR-0068](CASA-ADR-0068-memory-zone.md) (memory immutable), [CASA-ADR-0069](CASA-ADR-0069-memory-kinds-mutability.md) (earned postulate), [CASA-ADR-0062](CASA-ADR-0062-genetic-zone.md) (`promote_canon`), [CASA-ADR-0065](CASA-ADR-0065-controlled-mutations.md), [agent-existence-north-star.md](agent-existence-north-star.md) (самопочинка), KB: `agent-notes/knowledge/work/projects/door-to-singularity/ca-substrate-agent/note-casa-lived-experience-stop-continuity-v1.md`, `casa/prisms/memory/concept_layer.py`, `casa/prisms/memory/write_gate.py`, `casa/prisms/memory/agent_canon_lattice.py`, `casa/curriculum/concept_net.py`

---

## Context

### Что пошло не так

| Ожидание (0073 + нейронаука) | Факт в коде @ 2026-06-22 |
|------------------------------|---------------------------|
| Species catalog **concept cells** @ T=0 | P18 stub: **4** `concept.*` hub + alias glue |
| Curriculum ~280 concepts → **Built-In** neurons | Lab `lex.*` graph в `schema-math`; store teach C0 не сделан |
| `theories[]`: bootstrap + earned | `concept_layer`: один `species-concept-bootstrap-v1`; earned wire частично в `write_gate` |
| Ошибка в Built-In → агент **сам** пересматривает | `demote_canon` блокирует host bootstrap; нет **supersede** ceremony для concept domain |

**0083 §7 (устаревшая формулировка):** curriculum только как side-lattice `agent-curriculum-net`, **не** catalog `concept.*`. Это был компромисс C0 («не выглядеть как earned agency»), но **ломает** north star concept cells: authored species prior **должен** быть `concept.*` hub + `lex.{ru,en}.*`, не параллельный мир `lex.apple`.

### Операторский тезис (нормативный)

```text
Concept Zone
├── Built-In / Basics      — вид / curriculum @ T=0 (provenance: authored, не earned)
└── Self-Earned            — novel + исправления после verify (provenance: earned)

Все могут ошибаться: Built-In ≠ gospel. Агент исправляет через ceremony (supersede),
не через hot_write и не только через оператора /remember.
```

Связь с lived experience: субъект с траекторией может сказать «СТОП, в школьном словаре не так» — при наличии evidence + gate, не silent drift.

---

## Decision

### 1. Concept Zone = одна полка, две theory-ветки

**Не** новая intelligence zone. **Не** OntologyZone. Разделение — в `memory.immutable.domains.concept.theories[]` + `catalog` rows с `theory_id` / `provenance`.

```text
memory.immutable.domains.concept
├── theories[]
│   ├── { theory_id: species-concept-bootstrap-v1,
│   │     tier: built_in,
│   │     provenance: authored_species | operator_curriculum,
│   │     active: true|false,
│   │     superseded_by: null | earned-concept-correction-vN }
│   └── { theory_id: earned-concept-{slug},
│         tier: self_earned,
│         provenance: earned,
│         active: true|false,
│         supersedes: species-concept-bootstrap-v1? }
├── concept_ids[]          — union active theories (hub ids only)
├── catalog[concept.*]     — per-hub: lex, legacy, theory_id, indexed_at_tick
├── lattice_ids[]
│     agent-concept-core     — sparse hub index (P19)
│     agent-concept-graph    — type/isa/affords/relations (бывш. curriculum-net)
└── spawn_policy
      hot_write: forbidden
      promote: genetic.promote_canon
      supersede: genetic.supersede_concept_theory   ← NEW ceremony id (P20a)
      fork: theory_branch; append-only audit
```

| Tier | `theory_id` prefix | Кто пишет | Write context | Agency claim |
|------|-------------------|-----------|---------------|--------------|
| **Built-In** | `species-concept-*` | operator teach / bootstrap | `bootstrap`, `operator` | «вид дал словарь» |
| **Self-Earned** | `earned-concept-*` | agent after gate | `promote_canon`, `supersede_concept` | «сам вывел / пересмотрел» |

**Invariant:** `tier=built_in` **никогда** получает `provenance: earned`. `tier=self_earned` **никогда** маскируется под bootstrap.

### 2. Built-In = полноценные concept neurons (P18c target)

Curriculum base (`concept-net-base-v1.json`) teach **как Built-In catalog**, не как wholesale earned:

| Artifact | Normative id | Host |
|----------|--------------|------|
| Concept hub | `concept.{slug}` | `domains.concept.catalog` + index `C:concept.*` @ `agent-concept-core` |
| RU surface | `lex.ru.{slug}` | edge `E:concept.*:lex.ru.*` |
| EN surface | `lex.en.{slug}` | edge `E:concept.*:lex.en.*` |
| Types / relations | `type.food`, `on\|arg1\|…` | `agent-concept-graph` @ `prism_agent` |

**Teach API (C0+, amended):**

```text
ensure_concept_built_in(state, profile=base|wide)
  → spawn_concept_prism per hub (theory_id=species-concept-bootstrap-v1)
  → teach_concept_graph (isa, affords, relations) on agent-concept-graph
  → meta.concept_built_in: { bundle_hash, counts, taught_at }
```

**Anti-pattern (earned only):** mint ~280 hub **без** `tier=built_in` / **без** bootstrap context → ложная agency.

**Anti-pattern (0083 legacy):** держать species prior только на `lex.*` identity без `concept.*` hub.

**Migration:** Dima `lex.apple` → `concept.apple` + `lex.ru`/`lex.en`; read-path aliases `lex.*` → `concept.*` на переходный период.

### 3. Self-Earned — novel + correction

Два подтипа, один ceremony family:

| Kind | Пример | Gate |
|------|--------|------|
| **Novel hub** | `concept.{novel}` из multimodal bind | held-out + cross-surface honesty (0073 P18f) |
| **Bootstrap correction** | `concept.window` affordance / isa wrong vs life | conflict evidence + validate + held-out; **supersede** built-in row |

**Pipeline (correction):**

```text
1. Conflict detected
   validate/graph vs episodic bind / partner / vis imprint
   journal domain=self, status=confirmed (or gate with allow_unconfirmed)

2. Candidate in explicit / sandbox
   patch: { hub, edge_op, new_target, reason, test_cues[] }

3. supersede_concept_theory (P20a) OR promote_canon (novel only)
   held-out GateReport.passed == true  (or operator_sign for lab)
   → new theory row earned-concept-correction-v{N}
   → bootstrap theory: active=false, superseded_by=…
   → catalog[hub] points to correction theory for affected ids
   → audit: prior theory retained (append-only), not deleted

4. Read path
   active_theory_for_domain(concept) → merged catalog view
   provenance shows supersede chain
```

**Invariant:** λ=0 на **hub token** @ healthy agent — hub id **не** стирается; меняются **edges / graph / lex attachment** через supersede, не hot sleep merge.

### 4. Ceremony: `supersede_concept_theory` (P20a — spec)

Симметрия `agent_promote_canon_lattice` + `record_earned_postulate`, domain=`concept`.

| Field | Required |
|-------|----------|
| `supersedes_theory_id` | e.g. `species-concept-bootstrap-v1` |
| `new_theory_id` | `earned-concept-correction-v{N}` |
| `concept_ids` | hubs under correction (subset or full fork) |
| `patch` | graph/catalog ops (structured, auditable) |
| `source_journal_id` | self journal |
| `gate_report` | held-out pass **or** `operator_sign` |

**Запрещено:**

- hot_path / sleep_merge на `agent-concept-core` / bootstrap catalog
- `operator_sign` как единственный путь production (lab only)
- silent overwrite bootstrap JSON на диске без store ceremony
- удаление superseded theory из `theories[]` (только `active: false`)

**Разрешено оператору:** `bootstrap` / `operator` teach **нового** агента @ fork; **не** правка живого агента в обход ceremony (см. anti-patterns).

### 5. Связь с 0083 (curriculum @ store)

| 0083 (до amend) | 0085 (normative) |
|-----------------|------------------|
| curriculum → `agent-curriculum-net`, не catalog | graph → **`agent-concept-graph`**; hubs → **Built-In catalog** |
| `lattice_ids` only | `lattice_ids` + **`concept_ids`** @ `tier=built_in` |
| anti wholesale `concept.*` | anti wholesale **earned**; **authored Built-In wholesale — OK** |

`ensure_curriculum_ontology` → переименовать / делегировать в `ensure_concept_built_in` (один entry point).

### 6. Honesty probes (extended)

| Probe | Pass |
|-------|------|
| Built-In coverage | `catalog` count ≈ base profile (~280), `theory_id=species-concept-bootstrap-v1` |
| Cross-surface (0073 P18f) | sample hubs: RU/EN/legacy → same `concept.*` |
| Earned separation | no `catalog` row with `provenance=earned` without `promote_canon` / `supersede` audit |
| Supersede audit | if `active_theory ≠ bootstrap` → `superseded_by` chain present |
| Agency | life tick / listen **не** вызывают teach; correction **не** без gate |
| Math lattice clean | `schema-math` без food/isa edges (0083 postmortem) |

Artifact: `concept_honesty_report.json` — добавить `built_in` / `self_earned` / `active_theory` sections.

---

## Rollout

| Phase | Action | Depends |
|-------|--------|---------|
| **P0** | This ADR accepted | — |
| **P1** | Amend teach: `concept.*` + graph; aliases `lex.*` | 0083 P1 |
| **P2** | `theories[]` schema in `ensure_concept_domain`; catalog `theory_id` | P1 |
| **P3** | `supersede_concept_theory` stub + test (operator_sign) | P2, promote_canon |
| **P4** | held-out gate for correction path | P3, eval held_out_gate |
| **P5** | Navigator + 0083 §7 pointer; Dima sync | docs |

**Не блокирует** listen pilot G0, **блокирует** claim «полные concept cells на store» до P1–P2.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| 4 hub glue как «Concept Zone готова» | P18c Built-In catalog @ base |
| Curriculum `lex.*` as permanent identity | `concept.*` hub + locale lex |
| Built-In ошибка → только `/remember` оператора | supersede ceremony + agent journal |
| hot_write исправляет bootstrap | `supersede_concept_theory` |
| 280 hub без tier → looks earned | `tier=built_in`, `provenance=authored_species` |
| Удалить superseded theory | `active: false`, audit chain |
| Отдельная OntologyZone | `domains.concept.theories[]` |
| 0083 side-lattice-only forever | graph lattice + Built-In catalog (this ADR) |

---

## Open questions

1. **Fork @ reproduction:** Built-In общий `species_id`, Self-Earned corrections — в child genome или только episodic? (скорее: bootstrap копируется; earned corrections — character store, не species — уточнить с 0084.)
2. **Partial supersede:** один hub vs whole theory fork — v1: per-hub patch list inside one `earned-concept-correction-vN`.
3. **Wide profile:** 4500 Built-In — тот же tier; cell budget / index sharding (P19 scale).

---

## Summary

Concept Zone — **полка с двумя tiers** (Built-In / Self-Earned), не два мира id. Curriculum Димы — **Built-In concept neurons** (`concept.*` + graph). Ошибка в Built-In — **не** стыд и **не** вечность: агент исправляет через **supersede** с gate и audit, в духе memory immutable + north star самопочинки.
