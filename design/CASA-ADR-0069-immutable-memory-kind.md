# ADR-0069: Immutable memory kind — adopted postulates (canon lattices)

**Status:** accepted (design)  
**Date:** 2026-06-07  
**Related:** ADR-0068 (Memory Zone), ADR-0067 (zone prism wire), ADR-0062 (genetic / promote_canon), ADR-0065 (controlled mutations), ADR-0059 (innate basis), [prisms/memory/stack.json](prisms/memory/stack.json), [zone-prism-map.v1.json](zone-prism-map.v1.json)

---

## Context

**ADR-0068** ввёл Memory Zone с **Explicit / Implicit** и вынес **Immutable** в отдельный kind (не флаг `mutability` на explicit).

Обсуждение с оператором уточнило intent в три шага:

1. **Immutable — отдельное место** под решётки, sibling explicit/implicit, не «заблокированный explicit».
2. **Не «истина на века»** — законы природы люди *открыли*; аксиома — *принятое исходное положение* для теории; другие аксиомы → другая теория.
3. **Жизненный цикл** — @ bootstrap operator кладёт conventions; за жизнь agent экспериментирует в explicit, и через **promote_canon** может **создавать** новые immutable-решётки (earned postulates). Hot path по-прежнему не пишет в immutable.

```text
memory
├── explicit     … гипотезы, опыт, declarative drift
├── implicit     … навык, priors, priming
└── immutable    … принятые postulates/conventions (bootstrap or earned)
```

**Epistemic role:** `immutable` = **frozen assumptions for a theory**, not ultimate truth.

**P11 dry-run** (von-neumann) находит **4 bootstrap immutable lattices**: `alphabet-ru/en`, `syllables-ru`, `morph-role-ru` — classifier пока кладёт их в `explicit.semantic` + tag `mutability=immutable`. **Поведение близко; онтология — нет.**

---

## Problem

| Без отдельного Immutable kind | Риск |
|-------------------------------|------|
| Postulates лежат в том же pool, что lexicon shards | sleep merge, NCA train, bind budget **не отличимы** declaratively |
| «Доказали → навсегда в LTM» | путаем **открытое знание** (explicit) с **принятой посылкой** (immutable) |
| Genetic immutable смешивается с field | кажется, что «весь LTM sealed» или «ничего не sealed» |
| Sleep переписывает morph-role | ломается bind без ceremony |

**Цель:** третий ящик для **принятых postulates** — read stable, hot write forbidden, **promote path** для bootstrap и earned canon; experiential memory не конкурирует за drift path.

---

## Decision

### 1. Три memory kind (канон терминов)

| Kind | Вопрос | Hot path write | Promote path write | Read | Von-neumann v0 |
|------|--------|----------------|-------------------|------|----------------|
| **explicit** | *declarative, может меняться жизнью?* | ✅ hippo, journal, mutable LTM | — | ✅ | hippo, dialogue, lexicon-*, phrases-*, WM |
| **implicit** | *умею без формулировки?* | ✅ priors, NCA finetune | — | ✅ (effect) | intent_prism, `model.pt`, priming |
| **immutable** | *принятые postulates/conventions для theory?* | ❌ | ✅ `promote_canon` (0062) + verify (0065) | ✅ | alphabet-*, syllables-ru, morph-role-* |

**Invariant:** `memory_kind ∈ {explicit, implicit, immutable}` — **ровно один** на cataloged lattice / memory organ.

**Не путать:**

| Layer | Про что |
|-------|---------|
| **Genetic (0062)** | **алгоритм** promote_canon, θ, verify policy |
| **Memory immutable (0069)** | **контент поля** — конкретные postulate lattices |
| **Explicit semantic** | открытое / выученное / гипотеза **до** принятия как postulate |

Genetic — *как* попасть в immutable; Memory immutable — *что там лежит* после ceremony; explicit — *откуда* черновик и опыт.

### 2. Epistemic role: postulate, not truth

| ❌ Не значит | ✅ Значит |
|-------------|----------|
| «Истина в последней инстанции» | **Исходное положение**, принятое для работы |
| «Открыли → навечно canon» | **Открыли** → explicit; **приняли как аксиому** → promote → immutable |
| «Другие аксиомы = ошибка» | **Другие аксиомы = другая теория** (fork, не overwrite) |
| «Только operator @ bootstrap» | Bootstrap **или** agent earned @ promote |

**Примеры:**

| Содержимое | Epistemic | Kind |
|------------|-----------|------|
| Алфавит RU @ species install | convention (не innate у людей; install @ T=0) | immutable bootstrap |
| Morph-role table | grammar postulate set | immutable bootstrap |
| F=ma после curriculum + probes | *принятая* модель механики, не «истина мира» | immutable **earned** (future) |
| Гипотеза до verify | draft | explicit mutable / sandbox |
| Lexicon 50k | experiential semantic | explicit mutable |

### 3. Lifecycle: explicit → promote → immutable

```text
T=0 bootstrap
  operator install → immutable (provenance=bootstrap, theory_id=lang-ru-v1)
  alphabet, morph-role, syllables

T=life (explicit)
  experiment, probes, sandbox draft lattice
  hippo, lexicon drift, schema-math train

T=promote (ceremony, not hot path)
  genetic.promote_canon + verify (0065)
  → spawn OR re-tag lattice → memory_kind=immutable
  → agent MAY create new lattice id in immutable index
  provenance=earned, promoted_at_tick, from_lattice_id?, verify_ref

T=after promote
  read: always in scope
  hot write: forbidden
  revise: theory fork (new theory_id + new immutable branch), NOT sleep-merge overwrite
```

**Invariant:** sleep **не merge'ит** hippo → immutable без promote gate. Mutable LTM — default merge targets.

### 4. Theory fork (смена аксиом)

Смена postulate set — **не** in-place mutation:

```text
theory_id: mechanics-newton-v1
  immutable: canon-mechanics-newton

explicit: «не сходится в пределах c» 
  → new draft in sandbox

promote + new theory_id: mechanics-relativity-v1
  immutable: canon-mechanics-relativity   ← sibling lattice
  superseded_by / active_theory_ref on agent state
```

Старый immutable canon **остаётся** (audit, replay, curriculum history); active bind выбирает **active_theory_id** per domain/tract.

### 5. Что кладём в Immutable (v0 + roadmap)

| Входит @ v0 | Не входит (explicit mutable) |
|-------------|------------------------------|
| `alphabet-*`, `syllables-ru` | `lexicon-*` shards (50k — жизнь + NCA) |
| `morph-role-*` (`bootstrap_canon` в stack.json) | `phrases-*`, `L3_phrase_*` |
| Operator `immutable_lattice_ids` в manifest | Hippo, dialogue, journal |
| **Roadmap:** earned postulates via promote | `schema-math` **до** promote (explicit mutable) |

**Principle:** Immutable = **postulate/convention tier**, не «весь teacher KB». KB bulk → explicit unless operator **installs** as bootstrap postulate.

**Criterion (все «да»):**

1. NCA lattice content (не code, не genetic rule)?
2. Дальнейший bind/compose **опирается** на стабильность **в рамках theory_id**?
3. Изменение только через **promote** или **theory fork**, не wake/sleep drift?

### 6. Место в wire — Option A / B

#### Option A — **Catalog only** (рекомендуем старт)

```text
prism_memory.lattices{...}          ← физически как сегодня
intelligence_zones.memory.immutable
    ├── lattice_ids[]               ← bootstrap + earned
    ├── lattice_patterns[]
    └── theories[]                  ← theory_id, active, lattice refs
```

- **Pros:** zero LTM move; P11 `memory_kind=immutable`; sleep gate по index.
- **Cons:** router обязан различать kind в одном prism.

#### Option B — **`prism_immutable` sibling prism** (если A тесен)

```text
prisms
├── prism_memory      … explicit semantic (mutable)
├── prism_immutable   … postulate lattices only
├── prism_hippo       … explicit episodic
```

**Критерий A→B:** hot path или sleep хотя бы раз записали в postulate lattice — повторяющийся bug class.

#### Option C — z_band / prefix only — **не достаточно** без router + kind index.

### 7. Read / write / sleep

```text
WAKE hot path
  read:  explicit ∪ implicit ∪ immutable   (domain + active_theory_id)
  write: explicit, implicit, sandbox (0014)
  never: in-place write to memory_kind==immutable

PROMOTE path (agent or operator)
  source: explicit sandbox / draft lattice
  gate:   genetic.promote_canon + verify (0065)
  action: spawn lattice, append immutable index, set provenance
  agent MAY create new immutable lattice via this path only

SLEEP consolidate
  hippo → explicit.semantic (mutable only)
  skip:  immutable targets
  never: merge into immutable without promote

NCA train
  default: explicit mutable semantic only
  immutable: lab opt-in only

THEORY FORK
  new theory_id + new immutable branch
  no overwrite of prior postulate lattice in hot/sleep path
```

### 8. Routing + singleton topology (0067 + 0068 + 0069)

#### 8.1 One Immutable @ Memory (not per intelligence zone)

```text
intelligence_zones
├── memory.immutable          ← ONLY owner of postulate lattices
│   └── domains × theories[]  ← lang / math / vis partitions
├── linguistic                ← client: immutable_read_scope { domain: lang }
├── logical                   ← client: immutable_read_scope { domain: math }
└── executive                   ← union read on cross-domain bridge
```

**Не делаем:** `linguistic.immutable`, `logical.immutable` — возврат к 0067 «zone owns LTM subset».

Promote (bootstrap or earned) **всегда** lands in `memory.immutable.entries[]` with `domain` + `theory_id`. Intelligence zone may **initiate** promote; Memory **owns** result.

#### 8.2 Resolve

```text
memory.resolve(tract, client_zone)
  → memory_kinds[]
  → domains[]                      # from client immutable_read_scope + explicit scope
  → active_theory_id?              # per domain; executive selects @ cross-domain
  → lattice_ids[]

# discuss: immutable WHERE domain=lang + explicit lexicon/phrases
# math: explicit schema-math + immutable WHERE domain=math AND active theory
# math→verbalize: executive union read lang immutable + math explicit (+ optional math immutable)
```

**Cross-kind read:** linguistic **читает** `memory.immutable` filtered by `domain=lang`; **пишет** explicit/implicit/sandbox only. Logical — `domain=math`. Same catalog, different filters.

### 9. State block (target, Option A)

```text
intelligence_zones.memory
├── explicit …
├── implicit …
├── immutable                    ← singleton
│   ├── lattice_ids[]
│   ├── lattice_patterns[]
│   ├── write_gate_ref          genetic.promote_canon
│   ├── domains { lang, math, vis, … }
│   └── entries[]               per lattice metadata:
│         lattice_id
│         domain                lang | math | vis | …
│         provenance            bootstrap | earned
│         epistemic_role        postulate | convention
│         theory_id
│         promoted_at_tick      null @ bootstrap
│         verify_ref            null @ bootstrap
│         from_lattice_id       optional lineage
│         superseded_by         optional @ theory fork
├── theories[]
│   ├── theory_id
│   ├── domain
│   ├── active                  bool
│   └── postulate_lattice_ids[]
├── core_lattice_id
└── sandbox_lattice_id
```

**Namespace:** `agent.memory.immutable.*` (concepts on postulate lattices); `agent.memory.explicit.*` для гипотез и опыта.

**Per-lattice catalog (zone-prism-map):** `memory_kind`, `domain`, `provenance`, `theory_id`, `epistemic_role`.

**Intelligence zones (0061):** `immutable_read_scope: { domain, theory_ref }` — pointer only, no local postulate store.

### 10. Reconciliation с 0068 / P11

| Legacy | 0069 |
|--------|------|
| `mutability: immutable\|mutable` | `memory_kind: immutable` |
| immutable ⊂ explicit.semantic | immutable **sibling** of explicit |
| `memory_mutability_for_lattice()` | `memory_kind_for_lattice()` |

---

## Open questions (remaining)

### Q1 — Physical place: A vs B?

Option **A** @ P13; **B** по критерию hot-path leak.

### Q2 — `schema-math`

**Resolved (design):** explicit mutable **until** agent promote → immutable earned postulate under `theory_id` (e.g. `arithmetic-peano-v1`). Not bootstrap immutable @ v0.

### Q3 — Teacher bundles (50k lexicon)

**Resolved (design):** explicit mutable default. Operator **may** install subset as bootstrap postulates (exam corpus) — rare, manifest-listed.

### Q4 — Read priority

Morph + alphabet **always-on** in lang bind @ v0; tract-hints for optional syllables — tune in REPL verbose.

### Q5 — `agent-memory-*`

Catalog scratch — **explicit** or Self tier; **not** immutable unless promoted.

### Q6 — Seal ceremony

**Resolved (design):** no global `immutable_sealed_at_tick` required @ v0. **Per-lattice** metadata @ bootstrap; **per-promote** record @ earned. Genetic zone seal (0062) stays separate.

### Q7 — Active theory selection

How executive picks `active_theory_id` per tract (default species theory vs agent fork) — **P14** API stub.

---

## Rollout

| Phase | Action |
|-------|--------|
| **P13a** | ADR-0069 accepted; 0068 aligned; zone-prism-map `immutable` + metadata fields |
| **P13b** | Classifier: `memory_kind`, `provenance`; dry-run `by_memory_kind` |
| **P13c** | `ensure_memory_zone.immutable` index (Option A) |
| **P13d** | Sleep + field_write hot gate |
| **P13e** | `promote_canon` → append immutable + lattice spawn (earned path) |
| **P13f** | Theory fork metadata + MEMORY.md (bootstrap / earned postulates) |
| **P13g** | (Optional) `prism_immutable` wire split (Option B) |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Immutable = ultimate truth | Immutable = **adopted postulate / convention** |
| Discovered law → sleep merge to canon | Discover → explicit; **accept** → promote |
| Change axioms by overwriting lattice | **Theory fork** + new immutable branch |
| Immutable = флаг на explicit | Immutable = **kind** + catalog + metadata |
| 50k lexicon in immutable | Postulate tier only; lexicon explicit mutable |
| Agent hot path → morph-role-ru | Promote ceremony only |
| Per-intelligence immutable zone | Singleton `memory.immutable`; domain partitions |
| `linguistic.immutable` vault | `immutable_read_scope` filter on memory catalog |
| «Agent never writes immutable» | Agent writes **only** via promote_canon |
| Genetic rules in immutable tier | Genetic = how; immutable = what cells |

---

## Consequences

- 0068 §2 ссылается сюда для epistemic model + earned canon.
- P11: `memory_kind` + optional `provenance`, `theory_id`.
- `promote_canon` (0062) becomes first-class path into Memory immutable, not side CLI only.
- REPL/MEMORY.md: **Installed postulates** vs **Earned postulates** vs **Active theory**.

## Links

- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0067-zone-prism-wire-migration.md](CASA-ADR-0067-zone-prism-wire-migration.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [zone-prism-map.v1.json](zone-prism-map.v1.json)
