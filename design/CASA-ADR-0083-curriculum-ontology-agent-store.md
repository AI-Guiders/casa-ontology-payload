# ADR-0083: Curriculum ontology on agent store — authored school base before experiential tracks

**Status:** proposed (draft)  
**Date:** 2026-06-21  
**Provenance:** оператор + агент — sync с Dima отложен; listen/motor track нужен species prior для parse/validate до stream pilot (аналогия с младенцем: «фу/мм» идут из **вкуса/обоняния/осязания**, не из абстрактной «оси оценки» — см. § Context)  
**Related:** [CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) (amends §7 Concept Zone catalog), [CASA-ADR-0073-concept-layer-lexicalization.md](CASA-ADR-0073-concept-layer-lexicalization.md), [CASA-ADR-0081-lexical-slots-not-utterance-scripts.md](CASA-ADR-0081-lexical-slots-not-utterance-scripts.md), [CASA-ADR-0028-field-native-sensory-experience.md](CASA-ADR-0028-field-native-sensory-experience.md), [CASA-ADR-0060-emotional-zone.md](CASA-ADR-0060-emotional-zone.md), [CASA-ADR-0063-perceptual-zone.md](CASA-ADR-0063-perceptual-zone.md), [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md), [CASA-scratch-listen-0027-layer-map-v1.md](CASA-scratch-listen-0027-layer-map-v1.md), [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md), [ВАЛИДАТОР-СМЫСЛА-статус-и-план.md](ВАЛИДАТОР-СМЫСЛА-статус-и-план.md), KB: `agent-notes/knowledge/domains/agent-operations/playbook-agent-process-debt-amplifier-v1.md`, `casa/curriculum/concept_net.py`, `casa/curriculum/world.py`, `casa/prisms/memory/concept_layer.py`

---

## Context

### Два слоя «понятий» уже существуют и **не сшиты**

| Слой | Код | Где живёт сегодня | Роль |
|------|-----|-------------------|------|
| **Concept Zone (P18 stub)** | `concept_layer.py` | `immutable.domains.concept`, 4 hub @ bootstrap | wire + honesty probes; **не** полный species catalog |
| **Curriculum concept net (Dima)** | `curriculum/concept_net.py` | lab: `build_meaning_state()` → ephemeral state; lattice `schema-math` | authored ontology: isa/affords/validate, parse, situation fingerprint |

Listen/motor hot path (`run_life_tick`, imprint, motor speech) **не вызывает** curriculum. Chat `/meaning` строит **отдельный** meaning state и (при `route on`) может **обойти** life tick — lab only.

**Sensory stack (параллельный контур):** listen A/V pilot разложен по [CASA-scratch-listen-0027-layer-map-v1.md](CASA-scratch-listen-0027-layer-map-v1.md) — adapters `file_replay` / `file_replay_stream` → codecs → compositor (`listen_moment`, `womb_tick`). Curriculum teach **не** входит в этот стек; somatosensory (touch/taste/smell) — отдельный будущий tract, не swap aud/vis adapter.

### Зачем teach **до** stream / womb pilot

**Аналогия (честная):** у ребёнка «фу, бяка» / «мм, вкусно» / «твердое» / «воняет» — не из абстрактной **оси valence**, а из **конкретных модальностей**: вкус, обоняние, осязание (и позже — связка с опытом: «эту поганку — нет»). Сначала **каналы и различимость**, потом обобщения и слова.

**CASA сегодня (не путать с ребёнком):**

| У ребёнка @ рождение | У Neumann @ pilot |
|----------------------|-------------------|
| вкус / обоняние / осязание | aud + vis imprint ([ADR-0028](CASA-ADR-0028-field-native-sensory-experience.md)); gustation/olfaction/tactile **нет** |
| «фу/мм» сразу из сенсорики | limbic valence/arousal ([ADR-0060](CASA-ADR-0060-emotional-zone.md)) — уже **модельная** свёртка по life events, не язык кожи |
| oral exploration | motor babble + field phonation — другой контур |

Тезис **не** «у нас уже есть ось оценки как у ребёнка». Тезис: **без заложенной инфраструктуры** (сенсорные контуры + authored typed roles) глупо ждать, что агент **сам выведет** и disgust, и `edible`, из одного pixel stream.

**Authored curriculum** — параллель **не** limbic-осям, а **species typed vocabulary** (roles, relations, cross-lingual names): «существует проверяемая грамматика on/eat/agent», как у вида уже есть **форма** различения до личного опыта с поганкой.

- **Не заменяет** просмотр, imprint, surprise, field-native efferent.
- **Даёт substrate**, куда позже ложатся partner parse, validate-as-critic, situation «seen before», lex bridges к listen.
- **Не ожидать**, что Neumann **выведет** с нуля категории вроде `edible`, `agent`, `on|arg1|positionable` из Lalabook без subs/OCR в ближайшем горизонте.

**Authored** = JSON + build scripts (base curated, wide WordNet-augmented) — **не** induced from agent video experience.

---

## Postmortem: merge `develop` → listen/motor track (2026-06-21)

**Trigger:** после merge выяснилось, что lab curriculum (`world.py`, тесты) кладёт **ontology + morphology + clause grammar + software domain** в **`schema-math` @ `prism_math`** — в одну F0-решётку с math L0. Это **против** разнесения зон/призм (linguistic ≠ math), которое уже было в архитектуре.

### Что смотрели при merge (и что пропустили)

| Проверяли | Не проверяли |
|-----------|--------------|
| `orchestrator.py` — percept, `av_coactive`, motor speech сохранены | **куда** `teach_concept_net` пишет edges |
| конфликты `partner_speech_act`, `utterance_materialize` | **`LATTICE = "schema-math"`** в `world.py` / curriculum tests |
| listen hot path не вызывает curriculum | **zone separation** vs lab harness |
| — | gate: «еда не в `prism_math`» |

**Merge gate был:** «life tick + listen + motor не умерли». **Merge gate не был:** «lab code не узаконивает math-bucket для non-math».

### Хронология (git, факты)

| Когда | Что |
|-------|-----|
| **2026-05-31** | `schema-math` создан для **math L0** → `prism_math` (`ingest_math_bundle`) |
| **2026-06-01** | multi-prism / zones уже live |
| **2026-06-15** | Dima curriculum burst: **с day 1 POC** тесты делают `ingest_math_bundle` → `teach_*` в **`schema-math`** (единственный способ завести решётку в harness) |
| **2026-06-15 18:53** | `world.py` / `/meaning` — всё в одном `LATTICE` |
| **2026-06-21** | merge `7a7970ef` — **код curriculum в репо**, hot path не тронут |

`schema-math` к еде **не относится семантически** — это **lab shortcut**: «math ingest уже создаёт lattice id, пишем туда всё подряд».

### Что merge **не** сделал (важно)

- **Не** залил concept-net на `agents/von-neumann` store автоматически (teach C0 ещё не был).
- **Не** отменил zone separation на **listen / life tick / motor** hot path.
- **Да** принял в дерево паттерн, который **ломает** разнесение **в lab state** и **в тестах** — без ADR-gate.

### Normative после postmortem

1. **Curriculum ontology @ store** — только **`agent-curriculum-net`**, **не** `schema-math`, **не** `prism_math`.
2. **Concept Zone** — **полка** `immutable.domains.concept`: регистрируем **`lattice_ids`** (authored graph), **не** wholesale `concept_ids` catalog (~280 hub).
3. **`world.py` / `build_meaning_state()`** — **lab ephemeral only** до отдельного рефактора lab harness; **запрещено** на character store / resync default.
4. **Любой будущий merge** curriculum-слоя — checklist § Merge checklist ниже.

### Merge checklist (curriculum / zones)

- [ ] Новый teach **не** использует `schema-math` для non-math edges?
- [ ] Linguistic ontology **не** в `prism_math`?
- [ ] `domains.concept.concept_ids` count **не** скачет к размеру wide net?
- [ ] Hot path (listen, life tick, motor) **не** зависит от `build_meaning_state()`?
- [ ] Probe § Honesty «math lattice clean» green на target store?

---

## Problem

| Без teach на store | Риск |
|--------------------|------|
| Curriculum только в chat ephemeral state | stream + sleep **не накапливают** school ontology |
| Ожидание «выведет из видео» | нет parse/validate substrate @ partner text |
| Wholesale mint в Concept Zone | ложная agency: 4500 hub как «он сам понял» |
| Deep chat route on character | второй автор параллельно life tick |

**Цель:** один **persistent**, **idempotent** teach authored curriculum на **agent store** **до** Phase B stream pilot — **explicit** memory, **не** immutable Concept Zone catalog.

---

## Decision

### 1. Именование и граница ответственности

```text
curriculum ontology (authored)     ← этот ADR — teach на store, explicit
Concept Zone (concept.* hub)       ← ADR-0073 — scaffold + earned promote only
listen imprint (A/V/L3)            ← ADR-0028 — experiential, не text graph
partner efferent compose           ← ADR-0081 — field/slots, not clause oracle
```

**Invariant:** curriculum teach **не** является efferent author и **не** substitute для motor/listen hot path.

### 2. Lattice, prism, Concept Zone shelf

| Property | Value |
|----------|-------|
| **Lattice id** | `agent-curriculum-net` (**dedicated**; **never** `schema-math`) |
| **Host prism** | **`prism_agent`** (agent-owned explicit graph) — **not** `prism_math` |
| **Concept Zone** | register id in `memory.immutable.domains.concept.lattice_ids` + `provenance: authored_curriculum_v1` — **not** new rows in `concept_ids` catalog |
| **Memory kind** | explicit semantic F0 graph (isa, affords, arg1/arg2, glossary names) |
| **Source JSON** | `lab/curriculum/concept-net-base-v1.json` (pilot default) or `concept-net-wide-v1.json` (optional) |
| **Teach API** | `teach_concept_net(state, lattice_id, data)` — C0: net + glossary **only** (no clause/morph capstone in store teach) |
| **Meta** | `state.meta.curriculum_ontology`: `{schema_version, net_name, lattice_id, taught_at, counts, bundle_hash}` |

```text
memory.immutable.domains.concept          ← полка (0073)
├── concept_ids[]                       ← 4 hub + earned promote ONLY
├── lattice_ids[]                       ← agent-concept-core + agent-curriculum-net
└── spawn_policy                        ← hot_write off on catalog

prism_agent.lattices.agent-curriculum-net   ← F0 edges (food, eat, on|arg1|…)
prism_math.lattices.schema-math             ← math L0 ONLY (math.num.*, reading_context)
```

**Why not `schema-math`:** historical lab harness reused math ingest to **create** a lattice id; `strengthen_graph_edge` then mixed **food|isa|food** with **math.num.*** in the **same** bucket — undoing zone/prism separation **inside** `prism_math`. See § Postmortem.

**Anti-pattern:** повторный full teach каждый macro_tick или каждый chat line.

### 3. Idempotent teach (normative)

```text
ensure_curriculum_ontology(state, store_dir, *, profile="base"|"wide", force=False)
  if meta matches bundle_hash and lattice populated → NO_OP (report skipped)
  else → teach + persist + update meta
```

Operator tool: `tools/teach_curriculum_ontology.py --store DIR [--base|--wide] [--dry-run] [--force]`.

Optional: `resync_agent_store --teach-curriculum` (opt-in; **not** default — teach can be heavy).

### 4. base vs wide @ pilot

| Profile | Concepts | When |
|---------|----------|------|
| **base** | ~280 curated | **default** for von-neumann listen pilot |
| **wide** | ~4500 (+ WordNet layer) | lab / validator coverage grind; operator opt-in |

Wide **не** блокирует pilot; base достаточен для locative/transitive validate pattern («яблоко на столе», «стол не agent для eat»).

### 5. Что teach **не** делает

- **Не** mint'ит ~280/`concept.*` hub в `domains.concept.catalog` (wholesale import).
- **Не** пишет curriculum edges в **`schema-math`** или **`prism_math`**.
- **Не** включает chat deep routing (`looks_domain` → `answer_clause`) on character store by default.
- **Не** подменяет `build_meaning_state()` capstone (clause/morph/software) на store @ C0 — только concept net + glossary.
- **Не** заменяет `affect_after_listen_scene` или limbic bootstrap.
- **Не** claim «Neumann understood the cartoon» — только «school dictionary exists on field for future wire».

### 6. Hot path wire — **после** C0 (отдельные slices)

| Phase | Scope | Author? |
|-------|-------|---------|
| **C0** (this ADR) | teach on store + test parse/validate reads field | N/A |
| **C1** | partner text → `parse_graph` → `situation_memory` / scoring; `validate` as **critic** in provenance | **no** — Neumann compose unchanged |
| **C2** | `concept_hints` from parse → perceptual → motor (lex/A bridges) | hints only |
| **C3** | listen/vis ↔ concept stytovka @ sleep | joint design; **not** C0 |

Character chat: **`--no-route`** (or default route off for subject pilot) until C1 explicitly reviewed.

### 7. Связь с Concept Zone (0073) — **amended by [0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md)**

**C0 (this ADR):** teach graph + glossary on dedicated lattice @ `prism_agent` — placement gate, idempotent store.

**Normative target (0085):** curriculum → **Built-In** tier Concept Zone — `concept.*` catalog + `agent-concept-graph` (types/relations), не parallel `lex.*` identity forever.

```text
domains.concept (Concept Zone shelf)
├── theories[]
│   ├── species-concept-bootstrap-v1   ← Built-In (curriculum @ T=0)
│   └── earned-concept-*               ← Self-Earned @ promote / supersede
├── catalog: concept.apple, concept.window, …   ← ~base profile @ Built-In
├── lattice_ids: agent-concept-core, agent-concept-graph
│
agent-concept-graph (F0)
├── food|affords|edible, on|arg1|positionable
└── concept.apple|isa|food

experience ──earned──► promote_canon → NEW concept.*
bootstrap error ──agent──► supersede_concept_theory → correction theory (0085 §4)
```

**Anti-pattern (earned only):** ~280 hub **без** `tier=built_in` → false agency. **Authored Built-In catalog — OK** (0085 §2).

**C0 interim:** lattice id may remain `agent-curriculum-net` until P1 rename; **не** `schema-math`.

**Clean cut:** teach/read **only** `concept.*` + lemma `lemma.{ru,en}.*` on concept graph — **no** `lex.*` hub, **no** transitional alias layer. **missing map ≠ auto-promote**.

**`lang.word.*` lexicon store:** **не** мигрируем в этом ADR; coexist с Concept Zone (§2.2 в 0085).

**Lab legacy (`world.py`):** всё в `schema-math` — **не** модель store; refactor lab harness отдельно, не блокирует C0 store teach.

---

## Rollout

| Step | Action | Gate |
|------|--------|------|
| **P0** | This ADR accepted | — |
| **P1** | `ensure_curriculum_ontology` + CLI tool + unit test on fresh state | parse + validate smoke |
| **P2** | Teach **base** on `agents/von-neumann` (operator) | `meta.curriculum_ontology` present |
| **P3** | Listen pilot G0–G1 (scratch checklist) | imprint green |
| **P4** | C1 wire (separate PR) | no efferent oracle regression |
| **P5** | Scratch `G-pre` pointer in listen-wire-gap | docs only |

**Order vs listen:** **P1–P2 before** womb/stream Phase B — не блокирует cold ingest, блокирует **осмысленный** partner/validate wire later.

---

## Honesty / success criteria

| Probe | Pass |
|-------|------|
| Teach idempotent | second run → skipped, same `bundle_hash` |
| Field survives resync | `parse_graph(store_state, …)` non-empty for control clause |
| Category sanity | `validate(eat, стол, мясо).valid == False` on **`agent-curriculum-net`** |
| Agency preserved | no new `clause_*` efferent; chat route off on character pilot |
| Concept catalog unchanged | `len(domains.concept.concept_ids)` ≈ bootstrap (4 + earned), **≠** wide net size |
| **Math lattice clean (P2 gate)** | `schema-math` @ `prism_math` has **no** curriculum edges (`\|isa\|`, `\|affords\|`, `eat\|arg`, `lex.*\|isa\|`) |
| **Curriculum host correct** | edges live on **`agent-curriculum-net`**, registered in `domains.concept.lattice_ids` |

Artifact (optional): extend store `MEMORY.md` section «Curriculum ontology (0083)» via memory_map/resync — counts only, not full graph dump.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| «Curriculum = Neumann learned the video» | authored school base + experiential imprint separate |
| Mint wide net into Concept Zone **catalog** | teach graph lattice + earned promote to hub |
| `build_meaning_state()` on live store / each chat | once teach + meta gate; lab ephemeral only |
| **`LATTICE = "schema-math"` for food/morph/clause** | **`agent-curriculum-net` @ `prism_agent`** |
| Linguistic ontology in **`prism_math`** | math stays in `schema-math`; curriculum separate prism |
| Merge curriculum without lattice-placement review | § Postmortem merge checklist |
| Deep route before C1 review | life tick + field compose canonical |
| Wait for Dima sync to teach base | C0 local; Dima sync for capstone/T4 review later |
| Teach clause/morph capstone @ C0 store | concept net + glossary only; grammars @ C1 if needed |

---

## Open questions

### Q1 — Round-trip grammars in C0?

**Proposal:** C0 teaches **concept_net + glossary** only; `ru-rules` / clause grammars add when C1 needs `render` on store — avoid overscoping P1.

### Q2 — Manifest entry?

**Proposal:** defer `agent-bootstrap-manifest.v1.json` flag until P2 proven; cold bootstrap may call `ensure_curriculum_ontology(profile=base)` in P2b.

### Q3 — Wide on production von-neumann?

**Proposal:** operator choice; default **base** until storage/time budget measured.

---

## Summary (one line)

**INVARIANT:** Authored curriculum ontology is **taught once on the agent store** on **`agent-curriculum-net`** (under Concept Zone shelf, **not** `schema-math` / `prism_math`) as **species school prior** before listen stream pilot — **not** wholesale Concept catalog and **not** a substitute for field-native sensory imprint or efferent agency.

---

## Links

- [CASA-ADR-0073-concept-layer-lexicalization.md](CASA-ADR-0073-concept-layer-lexicalization.md)
- [CASA-ADR-0081-lexical-slots-not-utterance-scripts.md](CASA-ADR-0081-lexical-slots-not-utterance-scripts.md)
- [CASA-ADR-0028-field-native-sensory-experience.md](CASA-ADR-0028-field-native-sensory-experience.md)
- [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md)
- [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md)
