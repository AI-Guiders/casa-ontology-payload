# ADR-0073: Concept layer — языко-независимые «concept cells» vs лексикализация

**Status:** proposed (draft)  
**Date:** 2026-06-09  
**Related:** ADR-0061 (linguistic zone), ADR-0068/0069 (memory kinds), ADR-0070 (forgetting λ), ADR-0062/0072 (genome / fork), ADR-0065 (promote / distill), ADR-0036 (morphology — design ref), [CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md) (Built-In vs Self-Earned, supersede bootstrap), [meta_concept_aliases.py](../casa/prisms/memory/meta_concept_aliases.py), [design/РЕКОМЕНДАЦИИ-Von-Neumann.md](РЕКОМЕНДАЦИИ-Von-Neumann.md) §5, [agent-existence-north-star.md](agent-existence-north-star.md)

**Neuroscience refs (external):** Quian Quiroga et al., *Nature* 435 (2005) — invariant concept cells, MTL; multimodal percepts (PMC3032396); perspective *Neuron* 2026. ML: «Separating Tongue from Thought» (ACL 2025); cross-lingual shared neurons (ACL 2025); brain–LM shared conceptual space (arXiv:2506.20489).

---

## Context

### Что показала нейронаука (concept cells)

В медиальной височной доле (гиппокамп и окрестности) у человека записаны **отдельные нейроны**, которые:

- отвечают **избирательно** на один концепт (лицо, место, объект);
- **инвариантны** к виду стимула (разные фото, ракурс, контекст);
- **мультимодальны**: та же клетка может активироваться на **картинку, написанное имя и произнесённое имя**;
- кодируют **разреженно** (sparse) и **абстрактно** — не «каждую пору на лице», а «Jennifer Aniston как идея»;
- формируют связи **быстро** (порядка суток) и участвуют в переводе перцепта в **долговременную эпизодическую память**.

Это не метафора «слой идей» — это измеренный механизм. Для CASA важнее всего **разделение**: один стабильный концепт ↔ много поверхностных форм (визуальных, текстовых, аудио).

### Что показывают multilingual LLM + fMRI (2024–2025)

Параллельная линия (не замена concept cells, а **дополнение**):

- в трансформерах **язык вывода** кодируется **раньше**, чем **семантический концепт** (activation patching, ACL 2025);
- при обучении модели сначала строят **языко-специфичные** представления, затем они **сжимаются** в общие cross-lingual нейроны;
- encoding-модели, обученные на одном языке, **переносятся** на мозговую активность слушателей **другого** языка при той же истории — shared **supralingual** conceptual space.

**Вывод для архитектуры:** «окно» как идея **не должно** быть `lang.word.okno` или `en.word.window` — это две **лексикализации** одного `concept:window`.

### «Дети учат статистически, как LLM» — оговорка

Статистическое сегментирование речи у младенцев **реально** (переходные вероятности, distributional cues). Но:

| LLM-style | Ребёнок / CASA |
|-----------|----------------|
| миллиарды токенов | мало данных, **заземлено** (показали → назвали) |
| embedding cloud | **дискретный** концепт + provenance |
| генерация открытого текста | **compose** только из привязанных фреймов |

CASA **не** копирует LLM на hot path. Concept layer — это **concept cells + provenance**, не distributional prior. LLM допустим **только** на cold path дистилляции → гейт → promote (0065, рекомендации §4).

### Что уже есть в коде (частично)

| Паттерн | Пример | Оценка |
|---------|--------|--------|
| Языко-**независимый** мета-концепт | `lang.meta.letterCase.upper`, `lang.meta.compare.greater` | ✅ concept-like |
| Концепт **=** русская форма | `lang.word.apelsin`, `ru.dialog.*`, `ru.prop.*` | ❌ lexeme fused with concept |
| Миграция legacy → canon | `meta_concept_aliases.py` | ✅ precedent для split |
| Решётки по языку | `lexicon-ru`, `lexicon-en`, route by `grapheme.latn.*` | ⚠️ surface split без shared concept lattice |
| Intent / dialog tables | `semantic_read.py`, `ru.*` prefixes | ⚠️ EN = «месяцы `ru.* → en.*`» (рекомендации §5) |

**Инсайт (оператор, 2026-06-09):** искали «слой идей» — в нейронауке он уже назван (**concept cells**). В CASA его нужно **формализовать**, а не изобретать заново.

---

## Problem

| Без concept / lexeme split | Риск |
|----------------------------|------|
| `lang.word.X` = идея и русское слово | EN = дублирование всего `ru.*` |
| Роутер intent = RU surface tables | math/grammar/recall не переносятся на locale |
| Vis frame ↔ слово без общего id | нет мультимодального «одного нейрона» |
| Forgetting по lexeme | «забыли слово» = «забыли идею» |
| Immutable bootstrap | alphabet/morph immutable, **содержательные** концепты — нет |

**Цель:** **concept identity** (языко- и модальность-независимая) отделить от **lexicalization** (RU/EN surface, grapheme, syllable, morph) и **discourse frames** (locale-specific realizers).

---

## Decision (proposed)

### 1. Два слоя идентичности

```text
concept:{id}                    ← «concept cell» (sparse, invariant, provenance hub)
├── lex.ru.surface → "апельсин"   grapheme/syllable lattices (lexicon-ru)
├── lex.en.surface → "orange"     grapheme/syllable lattices (lexicon-en)
├── vis.frame_id   → retinal cue  (prism_visual)
├── audio.*        → (future perceptual)
└── meta.morph.*   → paradigm hooks (0036 — inflection as lex layer, not concept)

discourse.ru.* / discourse.en.*   ← compose realizers (0056), NOT concept identity
```

**Invariant:** один `concept:orange` активируется от RU-текста, EN-текста и vis-cue **через разные lex/vis edges**, но **один** concept token в bind budget.

### 2. Именование (normative v1)

| Layer | Prefix | Example | Memory kind (0068/0069) |
|-------|--------|---------|-------------------------|
| **Concept** | `concept.` | `concept.orange`, `concept.window` | **immutable** @ `domains.concept` (bootstrap or earned) |
| **Lexeme RU** | `lex.ru.` | `lex.ru.apelsin` → `concept.orange` | explicit.semantic |
| **Lexeme EN** | `lex.en.` | `lex.en.orange` → `concept.orange` | explicit.semantic |
| **Meta (grammar/epistemic)** | `lang.meta.` | `lang.meta.compare.greater` | immutable @ `domains.lang` |
| **Discourse frame** | `discourse.{locale}.` | `discourse.ru.self` (migrate from `ru.dialog.self`) | explicit / sandbox |
| **Legacy** | `lang.word.*`, `ru.*` | read-path aliases only | migrate → concept+lex |

**Anti-pattern:** новые `lang.word.{russian_surface}` как **identity** концепта.

### 3. Concept Zone — `memory.immutable.domains.concept` (не intelligence zone)

**Решение (оператор, 2026-06-09):** после завершения **Zones** (P11–P12) — выделить в immutable **Concept Zone**: место, где **безопасно** живут hub/prism на `concept.*`. Не 11-я intelligence zone; **полка** внутри singleton `memory.immutable` (0068 §4.1), sibling `domains.lang` / `math`.

```text
memory.immutable.domains.concept
├── theory: species-concept-bootstrap-v1
│     concept.orange   → lattice concept-orange  (or indexed cell @ agent-concept-core)
│     concept.window   → lattice concept-window
│     concept.door     → …
├── theory: earned-*   @ promote_canon only
│     concept.{novel}  → agent-discovered invariant (probes + verify)
└── spawn_policy
      hot_write: forbidden
      promote: genetic.promote_canon + honesty gate (§ below)
      fork: theory_id branch; supersede, not overwrite
```

**Зачем immutable, а не explicit:**

| explicit semantic | Concept Zone (immutable) |
|-------------------|--------------------------|
| lex drift, sleep merge | **λ=0** @ healthy agent (0070) |
| «забыли слово» | concept hub **остаётся** |
| гипотеза до verify | черновик в sandbox → **promote** → Concept Zone |
| нет ceremony | **один** путь добавить новый concept prism |

**«Концепты, которых мы не нашли»:** агент (или следующее поколение CASA) формирует **candidate** в explicit/sandbox (multimodal bind, cross-locale invariance) → `promote_canon` → новый `concept.{id}` + prism в `domains.concept`. Это **earned postulate**, не hot-path галлюцинация. Operator bootstrap @ T=0 задаёт **species scaffold**; earned расширяет каталог **внутри той же epistemic модели** (0069).

**Intelligence zones — клиенты Concept Zone:**

| Zone | Read |
|------|------|
| linguistic | `concept.*` + `lex.{locale}.*` |
| spatial | `concept.*` + vis edges |
| logical | `concept.*` + math bridges |
| social | `concept.agent.*`, partner model |
| executive | union read @ cross-domain tick |

**Prism-per-concept (target):** `spawn_concept_prism(concept_id)` → catalog entry under `memory.immutable.domains.concept` + optional dedicated lattice id `concept-{slug}`; v1 shared `agent-concept-core` with index (sparse, как concept cell literature).

### 4. Concept lattice (target)

Помимо per-language `lexicon-ru/en`:

```text
prism_memory / agent-concept-core   (or shared concept lattice in memory zone)
  token: C:concept.orange
  sparse activation; NCA repair allowed on experiential links, not on concept token @ healthy λ=0 policy for earned canon
```

**v0 rollout:** concept id в **explicit** semantic + **edges** в F0/graph к lex/vis (без отдельной 64×64 решётки).  
**v1 (Concept Zone live):** dedicated lattice or indexed cell per `concept.*` under **`immutable.domains.concept`** after P12g promote wire.

### 5. Bind / compose pipeline

```text
percept (text/vis) → locale surface tokens
                  → lex.{locale}.* lookup → concept.*
                  → bind budget on concept.* (NOT on surface string)
                  → discourse.{locale}.* realizers for utterance
```

**Intent routing (0061 linguistic):** tables keyed by **concept + locale surface**, not hardcoded `ru.dialog.*` in Python. EN = новый locale file, не fork логики.

### 6. Memory & forgetting (0069 / 0070)

| Object | Forgetting @ healthy | Notes |
|--------|----------------------|-------|
| `concept.*` hub @ **Concept Zone** | λ=0; demote/supersede ceremony only | immutable `domains.concept` |
| `lex.ru.*` / `lex.en.*` | normal episodic / priming | «забыл слово», не «забыл апельсин» |
| weak lex → strong concept | bind через concept hub | vis + один lex достаточно для compose |
| `lang.meta.*` bootstrap | λ=0 | 0069 |

### 7. Genetic fork (0062 / 0072)

| Invariant @ fork | Variable @ fork |
|------------------|-----------------|
| `concept.*` catalog (species) | lex weights, discourse tone |
| `lang.meta.*` topology | character_topology (0071) |
| promote algorithm id | forgetting_genotype alleles (0070) |

**Смысл:** дети **делят** «окно/дом/дверь», **расходятся** в lex access, character, forgetting — как phenotype priors, не как другой язык.

### 8. Distillation (0065 / рекомендации §4)

```text
LLM draft frame → adversarial gate (0037 ref) → candidate concept.orange + lex.ru.*
  → promote_canon (0069) → immutable OR explicit with high θ
```

Runtime **без** LLM. Concept layer **усиливает** gating: promote привязывает **concept id**, не строку.

---

## Honesty gate (pre-registered probes)

Мотивировано concept-cell literature + ADR-0070/0072 discipline.

**Corpus:** фиксированный набор `concept:{id}` с ≥2 lex (RU+EN) и ≥1 vis frame.

| Probe | Pass | KILL |
|-------|------|------|
| **Cross-surface activation** | bind на `concept.orange` от RU text, EN text, vis — **same concept id** in provenance | разные concept ids за одну идею |
| **Sparse invariant** | concept hub degree bounded; no «every lexeme is its own concept» | >80% lexemes without concept hub @ teaching store |
| **Lex-only forget** | decay `lex.en.*` does **not** drop `concept.*` votes below compose threshold if `lex.ru.*`+vis hold | concept votes collapse when one lex fades |
| **Locale router** | swap locale table EN; **same** concept bind for «window» / «окно» | duplicate `ru.prop` / `en.prop` logic in code |

**Артефакт:** `concept_honesty_report.json` @ P18f.

---

## Migration

### Phase map (legacy → target)

| Legacy | Target |
|--------|--------|
| `lang.word.apelsin` | `concept.orange` + `lex.ru.apelsin` |
| `lang.meta.*` | **keep** (already concept-like) |
| `ru.dialog.self` | `discourse.ru.self` + bind `concept.agent.self` |
| `ru.prop.*` | `concept.*` + `discourse.ru.*` realizer |
| `meta_concept_aliases` | extend → `CONCEPT_LEX_ALIASES` + migration CLI |

**Tool (target):** `python -m casa.cli migrate_concept_lex_split --store DIR --dry-run`

**Read path:** `canonical_concept_id()`, `lex_for_locale(concept, locale)` — symmetric to `canonical_lex_concept_id()`.

---

## Open questions

### Q1 — `concept.*` namespace flat vs typed?

**Proposal:** flat `concept.orange`; optional tags `domain:object`, `theory:naive-physics` in metadata — не в id string v0.

### Q2 — Discourse migrate `ru.dialog.*` → `discourse.ru.*` breaking?

**Proposal:** read aliases one release; write new ids only.

### Q3 — Separate concept lattice v0 or graph-only?

**Proposal:** graph-only **до** P12g; Concept Zone prisms in **`immutable.domains.concept`** @ P18g (after Zones done). Shared `agent-concept-core` index v1 when honesty probe passes.

### Q5 — Concept Zone vs 11th intelligence zone?

**Proposal:** **нет** новой intelligence zone. Concept Zone = **immutable partition** only; all intelligence zones read via `immutable_read_scope: { domain: concept }` or global concept union @ executive.

### Q4 — Statistical learning module?

**Proposal:** **optional** cold-path ingest (segment co-occurrence → **candidate** lex→concept edges), never hot compose. Отдельный ADR if implemented.

---

## Rollout

**Порядок:** **P11 → P12 (включая P12g–h immutable index) → P18**. Concept Zone без promote gate = anti-pattern.

| Phase | Action | Depends |
|-------|--------|---------|
| **P18a** | ADR-0073 + manifest `concept_layer` + `immutable.domains.concept` | **P12g–h** |
| **P18b** | `concept.*` / `lex.{ru,en}.*` schema + alias read path | P18a |
| **P18c** | migrate top N teaching concepts → **Concept Zone bootstrap** | P18b |
| **P18d** | bind budget on `concept.*`; provenance shows concept id | P11 wire |
| **P18e** | locale tables for intent (`discourse.{locale}.*`) | P18d |
| **P18f** | **Honesty gate** report | P18c–e |
| **P18g** | `spawn_concept_prism`; promote → `domains.concept` earned theory | P12g promote_canon |
| **P19** | `agent-concept-core` index + NCA policy on concept hub edges only | P18g; 0070 P15d |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| `lang.word.{surface}` as concept identity | `concept.*` + `lex.{locale}.*` |
| EN = copy all `ru.*` ids | locale discourse tables + shared concept |
| LLM embeddings on hot path | LLM → gate → promote concept |
| «Concept cell» = one Python object per word | sparse hub + multimodal edges |
| Забывание lex = забывание concept | λ on lex; concept protected @ healthy |
| Skip honesty probes | P18f cross-surface report |
| Concept prism in explicit without promote | Concept Zone @ immutable only |
| 11th intelligence zone «concept» | `memory.immutable.domains.concept` |
| Claim «exactly like human neuron» | «motivated by concept-cell + cross-lingual evidence» |

---

## Consequences

- Формализует «слой идей», который искали интуитивно — с опорой на измеренную нейронауку и cross-lingual ML.
- **Снимает** главный барьер EN (рекомендации §5): не дублировать онтологию, добавить locale.
- Усиливает **provenance** (ответ → `concept.orange`, не строка «апельсин»).
- Stыкует immutable (0069), forgetting (0070), genetic fork (0072) на **одной** идентичности концепта.
- Требует миграции store и bind — **не** вечерний патч; read-path aliases снижают риск.

## Links

- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0069-immutable-memory-kind.md](CASA-ADR-0069-immutable-memory-kind.md)
- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)
- [CASA-ADR-0072-genetic-weather-cross.md](CASA-ADR-0072-genetic-weather-cross.md)
- [design/РЕКОМЕНДАЦИИ-Von-Neumann.md](РЕКОМЕНДАЦИИ-Von-Neumann.md)
