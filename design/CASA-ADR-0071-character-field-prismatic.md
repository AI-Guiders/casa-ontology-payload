# ADR-0071: Character field — призматический темперамент (не плоская шкала)

**Status:** proposed (draft)  
**Date:** 2026-06-08  
**Related:** ADR-0057 (situations + character), ADR-0058 (limbic affect), ADR-0060 (emotional zone), ADR-0061 (character zone), ADR-0062 (genetic phenotype priors), ADR-0065 (fork / allelic), ADR-0067 (domain routing), ADR-0068 (memory domain scopes), ADR-0070 (forgetting modulators), ADR-0056 (discourse budget)

---

## Context

**ADR-0057** ввёл **character prism** — медленный prior, который субъект **сам** накапливает из ситуаций; не persona-script, не плоский JSON оператора.

Классическая психология описывает личность **плоскими шкалами** (Big Five, MBTI): одно число 0…100 на ось («невротизм», «интроверсия»). Это **проекция** сложного состояния для отчёта человеку, не механизм мозга.

В CASA у агента уже есть **другое основание**:

| Плоская психология | CASA |
|--------------------|------|
| `anxiety = 0.7` на всю жизнь | поле gain/bias, привязанное к **domain × situation** |
| тест раз в год | **медленная EMA** каждый эпизод (0057) |
| genotype → статистический риск | **genome → стартовая топология** маски (0062 §3) |
| один слайдер | **призма / решётка** в Character zone |

**Инсайт (оператор + Orion, 2026-06-08):** «черта характера» — не scalar, а **геометрия проводимости** на поле (вплоть до `64×64`), накопленная поверх limbic/social episodic. Пример: после провалов на math — «вмятина» в координатах `domain=math`; в `domain=lang` — ровная проводимость → **локально тревожный математик, уверенный гуманитарий**.

**Связь с размножением:** genetic fork задаёт **стартовую топологию** character field; unroll из `H_mix` — **0072** `weather_cross`.

---

## Problem

| Без призматического character | Риск |
|-------------------------------|------|
| Один scalar на агента | math-stress красит весь compose |
| Operator JSON «стиль речи» | Track A persona, не субъект (0057 anti-pattern) |
| Character без domain index | не стыкуется с 0067/0068 routing |
| Только flat digest в MEMORY.md | путаем проекцию и источник истины |
| Fork меняет только `zone_proportions` | голоса не расходятся в **форме** чувствительности |

**Цель:** character как **пространственный фильтр контекста** + **gain-слой** для neuromodulator/compose/forgetting; плоские оси — только **digest** для человека.

---

## Decision (proposed)

### 1. Три временных слоя (из 0057, не смешивать)

| Слой | Скорость | Поле | Character role |
|------|----------|------|----------------|
| **Tactic** | tick | bind, tract, limbic | читает mask, не пишет |
| **Habit** | эпизоды | WM, journal | теги для EMA |
| **Character** | медленно | character field | **write** @ consolidate |
| **Affect** | tick → медленно | limbic (0058) | **вход** в EMA character |

Character **не** заменяет limbic; он **запоминает форму** того, как limbic+опыт смещали поведение в разных доменах.

### 2. Character field — не одна ось, а индексированное поле

#### v0 (rollout first): матрица `domain × tract`

Низкоразмерный старт без полной `64×64`:

```text
character_bias[domain][tract]  →  gain multiplier
  domain ∈ { lang, math, social, … }     # 0068 scopes
  tract  ∈ { discuss, math, repair, … }
  value  ∈ ℝ  (default 1.0), EMA update
```

Уже даёт «плоский невротизм не на всё поле». Duck test 0057: после серии math-fail — `character_bias[math][*]` ↓ без сдвига `lang`.

#### v1 (target): lattice `agent-character-core` (64×64)

```text
prism_character / agent-character-core
  S[x,y]  — slow bias / conductance map
  index:  cell (x,y) ↔ (domain_bucket, tract_bucket, situation_tag)
```

**Индекс обязателен** (контракт с 0067): ячейка без семантического bucket — anti-pattern (opaque noise).

```text
character_index.v1:
  buckets:
    - domain: math, tract: math, tag: surprise_fail  →  region R1
    - domain: lang, tract: discuss, tag: repair_ok   →  region R2
```

EMA после consolidate:

```text
S[region] += α_char × Δ_episode
α_char ≤ genetic ema_limits.character_alpha_default
Δ from limbic snapshot + outcome (success/fail/repair)
```

### 3. Три механизма применения

#### 3.1 Context Bias Grid (пространственный фильтр)

На read (каждый tick):

```text
RouteContext { domain, tract, situation_tags }
  → lookup character mask M (matrix v0 or lattice region)
  → reweight bind candidates / DiscourseBudget.score_floor (0056)
```

Высокий bias → легче compose в домене; «вмятина» → торможение, defer, выше surprise sensitivity.

#### 3.2 Character-driven routing (gain на подкорку)

```text
M(domain, tract) → neuromodulator scale (0066 ceilings)
                 → forgetting β_eff scale (0070) в этом domain
                 → tract_competition prior (0052)
```

Характер **физически** меняет траекторию мышления через gain bus, не через новые строки в bundle.

#### 3.3 Genetic topology @ T=0 (fork)

```text
genetic_zone.character_topology
  ├── ema_alpha_default
  ├── initial_bias_grid_ref      neutral | allelic_warp
  └── domain_sensitivity[]       birth gains per domain
```

При fork (**0072**): `weather_cross` деформирует стартовую маску из `H_mix` → **другой голос @ tick 0** при том же species bootstrap (immutable language pack).

### 4. Плоская проекция ≠ источник истины

```text
Character field (many-D)  ──project──►  MEMORY.md digest
                                       «тревожнее в math: 0.72»
```

Оператор и curriculum читают **digest**; tick loop читает **поле**. Проекция — mean/max по `domain=math` или PCA на lattice — implementation detail.

### 5. Zone placement (0061)

| Property | Value |
|----------|-------|
| Zone id | `character` |
| Tier | innate intelligence (Tier 0), slow |
| Core | `agent-character-core` lattice (v1) или `character_bias` matrix (v0) |
| Sandbox | v0: none (0057); roadmap: `agent-character-sandbox` для lab |
| Writes | **только** subject-side consolidate; не teacher patch |
| Reads | executive, linguistic, logical, social clients via `character_prior(context)` |

**Не Memory Zone:** character — **intelligence zone** (как думать/реагировать), не LTM content (0068).

### 6. State block (target)

```text
intelligence_zones.character
├── core_lattice_id              agent-character-core (v1)
├── bias_matrix                  domain×tract (v0)
├── character_index_ref          character_index.v1.json
├── last_consolidate_tick
├── ema_alpha                    from genetic
├── genetic_topology_ref         genome.character_topology
└── digest                       flat summary for MEMORY.md
```

### 7. API (target: `casa/prisms/character/`)

| Function | Role |
|----------|------|
| `ensure_character_zone` | wire under intelligence_zones.character |
| `spawn_character_zone` | neutral grid @ T=0 + genetic warp |
| `character_prior` | `RouteContext` → bias matrix / region gains |
| `character_apply_compose` | scale DiscourseBudget / reweight blocks |
| `character_apply_gains` | neuromodulator + forgetting modulators |
| `character_consolidate_update` | post-sleep EMA from episodic + affect |
| `character_digest` | many-D → flat report |
| `character_snapshot` | REPL verbose |

### 8. Rollout

| Phase | Action |
|-------|--------|
| **P4a** | ADR-0071; v0 `domain×tract` bias matrix |
| **P4b** | `character_consolidate_update` after sleep |
| **P4c** | wire `character_apply_compose` (0056 budget) |
| **P4d** | duck test 0057 situation probe |
| **P4e** | `agent-character-core` lattice + index (v1) |
| **P4f** | genetic `character_topology` @ fork (0062) |
| **P4g** | `weather_cross` unrolls child topology (0072) |

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Character = Big Five JSON от оператора | поле из episodic EMA |
| Один scalar `openness` на весь агент | domain×tract или indexed lattice |
| 64×64 без index buckets | `character_index.v1` ↔ domain/tract |
| LLM / prose soul doc в веса | limbic + consolidate only |
| Плоский digest пишет в lattice | digest read-only projection |
| Character owns lexicon | character biases **read** memory scopes |
| Ручные bias matrices от teacher | genetic @ fork + life EMA |

---

## Open questions

### Q1 — Первая ось vs сразу lattice

0057: одна ось для duck test. **Proposal:** v0 = domain×tract matrix (уже 2D); v1 lattice.

### Q2 — Индекс regions: manual manifest или learned cluster

**Proposal:** manifest buckets @ v1; experiential не двигает bucket boundaries.

### Q3 — Character sandbox (0014)

Нужен ли lab sandbox для «что если другой темперамент» — P4+.

---

## Consequences

- Закрывает зазор «плоская психология vs CASA геометрия».
- Стыкует 0057 character с 0067/0068 domain routing.
- Genetic diversity (0062) включает **форму** character, не только proportions.
- Fork `weather_cross` (0072) — внешняя энтропия для child genome + topology.

## Links

- [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0072-genetic-weather-cross.md](CASA-ADR-0072-genetic-weather-cross.md)
- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0070-forgetting-policies.md](CASA-ADR-0070-forgetting-policies.md)
