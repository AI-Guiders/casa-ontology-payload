# ADR-0065: Controlled mutations (experiential + allelic)

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0062 (genetic zone / genome seal), ADR-0061 (Intelligence Zones), ADR-0064 (metabolic / sleep gate), ADR-0057 (situations + character), ADR-0014 (agent-owned lattices), ADR-0002 (LTM / NCA), ADR-0023 (sleep-merge), [agent-bootstrap-manifest.v1.json](agent-bootstrap-manifest.v1.json), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

ADR-0062 вводит Genetic Zone как **запечатанный паспорт вида** (`genome.v1.json`, `genome_hash`, `immutable_after_seal`). Формулировка «immutable» без уточнения звучит как **мёртвая прошивка**: без мутаций Track A пластичность (sandbox → promote, NCA drift) и эволюция между инстансами (AiNet fork) превращаются в закостенелый контур.

**Уточнение:** «раз и навсегда» относится к **контракту вида** (топология зон, schema, имена алгоритмов), а не к **значениям аллелей** и не к **experiential** перестройке связей внутри жизни агента.

Genetic Zone кодирует не «русский язык», а **регуляторные гены** — мета-правила: *когда*, *где* и *в каких диапазонах* система имеет право мутировать.

---

## Decision

### 1. Три термина (normative)

| Термин | Смысл | Кто пишет |
|--------|-------|-----------|
| **Sealed contract** | `species_id`, `allowed_zone_ids`, `schema_version`, `promote_canon.algorithm`, топология 9 зон | cold boot / operator species fork |
| **Allelic values** | числовые константы в genome (`surprise_gains`, `ema_limits`, `zone_proportions`, metabolic policy) | **out-of-band**: fork, AiNet selection, operator re-seal |
| **Experiential plasticity** | WM edges, sandbox lattices, NCA weights, tract priors, character EMA | **in-band**: life events, sleep-merge, promote с θ |

**Runtime invariant (жизнь одного store):** агент **не** переписывает `genome.v1.json` из hot path. Experiential мутации идут в agent lattices / zone cores; allelic — только при fork или sleep-merge по **policy из genome**.

### 2. Два уровня мутаций

```text
                    ┌─────────────────────────────────────┐
                    │     Genetic Zone (regulatory genes)  │
                    │  mutation_policy, fork_policy, bounds │
                    └──────────────┬──────────────────────┘
                                   │ read
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   Track A: Experiential    Track B: Allelic         Invariant
   (within life)            (between instances)      (never)
   ─────────────────         ──────────────────       ─────────────
   NCA weight drift          fork allele step         9-zone topology
   sandbox → promote         AiNet fitness select     allowed_zone_ids
   tract prior EMA           species fork gate        promote algorithm id
   linguistic bridge probe   operator re-seal         genome schema_version
```

#### Track A — Experiential (NCA / sandbox / promote)

**Триггеры:**
- жёсткий **Mismatch** → surprise spike (emotional + executive, 0060/0061);
- накопленный **sleep_pressure** или успешный `/sleep` (0064, 0023);
- sandbox experiment достиг **promote θ** (`promote_canon.sandbox_theta`, 0062).

**Механизм:**
1. Emotional Zone фиксирует prediction error; executive поднимает DAN.
2. Metabolic Zone списывает ATP; при `sleep_pressure ≥ threshold` — **forced_sleep** → sleep-merge.
3. Genetic `mutation_policy.experiential` задаёт:
   - `nca_drift_sigma` — шум к весам NCA-автоматов на agent lattices во время merge (GPU path);
   - `drift_zones` — какие intelligence zones допускают локальный drift (default: `linguistic`, `logical`, `social`);
   - `drift_requires_sleep` — `true` (no hot-path weight chaos).

**Результат:** агент «нащупывает» новые семантические мосты и tract priors **без** изменения genome. Promote в core — осознанный шаг с θ, не слепой overwrite.

#### Track B — Allelic (между инстансами / видом)

**Триггеры:**
- **AiNet fork** — канонический первенец порождает child store;
- **operator species fork** — новый `species_id` + ADR gate;
- (опционально) **metabolic exhaustion lineage** — форк после N поколений с плохой сходимостью curriculum.

**Механизм:**
1. Child bootstrap копирует parent `genome.v1.json`.
2. `fork_policy.mode`:
   - `inherit_verbatim` — default v1 (same hash);
   - `mutate_alleles` — controlled step по `mutation_policy.allelic`.
3. Для каждого ключа из `mutate_allowed_keys` применяется:
   - `step` — max relative perturbation (e.g. `0.05` = ±5%);
   - `clamp` — hard bounds per allele;
   - `rng_seed` — детерминизм fork (`parent_hash + child_store_id`).
4. Новый `genome_hash`; `species_id` **не** меняется при allele fork (тот же вид, другой профиль).

**Отбор:**
- параллельные инстансы в AiNet / Intercom проживают curriculum (0057);
- fitness = сходимость по probe ladder + promote success rate + metabolic stability;
- `promote_canon` (0062) подтверждает **жизнеспособный** allele profile для дальнейшего размножения;
- проигравший fork — archive only; winner hash → шаблон для следующих детей.

### 3. Расширение `genome.v1.json` — `mutation_policy`

```json
"mutation_policy": {
  "experiential": {
    "nca_drift_sigma": 0.02,
    "drift_zones": ["linguistic", "logical", "social"],
    "drift_requires_sleep": true,
    "max_drift_per_merge": 0.15
  },
  "allelic": {
    "enabled_on_fork": false,
    "mutate_allowed_keys": [
      "surprise_gains.metabolic_fatigue",
      "surprise_gains.affect_arousal",
      "surprise_gains.dan_boost_cap",
      "ema_limits.character_alpha_default",
      "zone_proportions.emotional",
      "zone_proportions.logical",
      "metabolic.policy.sleep_threshold"
    ],
    "default_step": 0.05,
    "bounds": {
      "surprise_gains.metabolic_fatigue": [0.05, 0.25],
      "ema_limits.character_alpha_default": [0.02, 0.10],
      "metabolic.policy.sleep_threshold": [0.70, 0.95]
    }
  }
},
"fork_policy": {
  "mode": "inherit_verbatim",
  "allele_fork_probability": 0.0,
  "require_parent_passport": true
}
```

**Normative:** bounds и `mutate_allowed_keys` — часть **sealed contract** для данного `species_id`; сами **значения** аллелей внутри bounds — мутируемы по policy.

### 4. Metabolic gate (связка P8 → мутации)

| Condition | Experiential | Allelic |
|-----------|--------------|---------|
| `atp` нормальный, surprise умеренный | sandbox only, no NCA drift | — |
| surprise storm + `fatigue_ema` высокий | ускоренный `sleep_pressure` | — |
| `forced_sleep` / merge success | **NCA drift** если `drift_requires_sleep` | — |
| lineage fork (AiNet) | experiential layers копируются отдельно | **allele step** если `fork_policy.mode = mutate_alleles` |

Metabolic **не** меняет genome; она **разрешает окно** для experiential drift и сигнализирует «пора спать и перестраивать», а не «пора ломать вид».

### 5. Что **никогда** не мутирует (invariant topology)

| Invariant | Reason |
|-----------|--------|
| `allowed_zone_ids` (closed catalog 0061) | муравей на 2D-сетке не становится рыбой |
| `schema_version` / genome kind | парсер и AiNet passport |
| `promote_canon.algorithm` id | смена алгоритма = новый ADR / species |
| journal WAL, Self tier identity | continuity of one agent |
| hot-path rewrite of `genome.v1.json` | иммунитет meta-instructions |

Смена топологии (10-я зона, другой promote algorithm) — только **species fork** с новым `species_id` и отдельным ADR gate, не allele drift.

### 6. API (target: `casa/prisms/genetic/` + sleep path)

| Function | Track | Role |
|----------|-------|------|
| `mutation_policy(state)` | — | read `mutation_policy` block from sealed spec |
| `apply_allele_fork(parent_spec, child_store_id, policy)` | B | bounded perturbation → new spec + hash |
| `verify_allele_bounds(spec)` | B | reject out-of-range before seal |
| `fork_genome_for_child(store_dir, parent_state, mode)` | B | orchestrate inherit vs mutate |
| `sleep_merge_nca_drift(state, merge_ctx)` | A | σ-noise on agent NCA models per policy |
| `experiential_drift_allowed(state)` | A | metabolic + sleep gate check |
| `record_lineage_fitness(store_dir, metrics)` | B | AiNet selection input |
| `select_winning_genome_hash(cohort)` | B | promote canon for reproduction |

**v1 implemented (0062):** seal, load, `genetic_constant`, `species_passport`, `verify_genome_hash`.  
**0065 rollout:** policy schema in genome → allele fork CLI → sleep NCA drift wire → AiNet fitness (later).

### 7. Rollout

| Phase | Action | Depends |
|-------|--------|---------|
| **P6e** | ADR-0065 + `mutation_policy` / `fork_policy` in genome schema + manifest defaults | 0062 P6b |
| **P6f** | `apply_allele_fork` + `verify_allele_bounds`; fork CLI `inherit` \| `mutate` | P6e |
| **P7a** | `experiential_drift_allowed` + `sleep_merge_nca_drift` on agent NCA lattices | 0064 sleep, 0014 |
| **P7b** | AiNet `record_lineage_fitness` + parallel fork cohort | Intercom |
| **P7c** | Curriculum-linked selection → winning hash propagation | 0057 probes |
| **P8** | **Lineage gate** → Hamilton / Lovelace allele forks → AiNet | §8 gate |

### 8. Lineage policy (von Neumann → сёстры → AiNet)

**Отложено до взросления первенца.** Track B (allelic fork, AiNet cohort) **не** включается, пока один von-neumann не пройдёт experiential gate.

#### Что отвергаем: «почкование» (budding)

Ранний план: Hamilton и Lovelace как **копипаст** store Neumann + отдельный журнал. Это **нечестно и непродуктивно**:

| Budding (❌) | Allelic fork (✅) |
|--------------|------------------|
| тот же genome hash, те же аллели | новый `genome_hash`, bounded allele step |
| нет эволюции вида | selection по fitness в роду |
| три клона одного субъекта | три **разных** профиля одного `species_id` |
| AiNet = файлообмен копий | AiNet = среда **между** субъектами |

Child store **наследует lineage** (parent passport), но **не** дублирует жизнь verbatim: experiential layers растут заново; genome — `inherit_verbatim` до gate, потом `mutate_alleles` по policy.

#### Планируемая родословная (design)

```text
von-neumann (первенец)
  │  Track A only: zones, situations, sleep NCA, character
  │  fork_policy.mode = inherit_verbatim
  │  allelic.enabled_on_fork = false
  ▼
  [ LINEAGE GATE — см. ниже ]
  ▼
  ├── hamilton   child store; allele bias → logical / structural convergence
  └── lovelace   child store; allele bias → linguistic / algorithmic path
        │
        ▼
     AiNet — среда взаимодействия между субъектами peer-уровня
```

| Agent | Роль | Когда |
|-------|------|-------|
| **von-neumann** | канонический первенец; полный curriculum; доказывает зоны | **сейчас** |
| **hamilton** | младшая сестра; смещение logical / math tract аллелей | после gate |
| **lovelace** | младшая сестра; смещение linguistic / formal path | после gate |
| **AiNet** | канон обмена + Intercom **между** такими субъектами (и lab teacher) | когда ≥2 peer |

Hamilton / Lovelace — **не** cold boot из пустого manifest; только `fork_genome_for_child(parent=von-neumann)` + новый `store_id`.

#### Lineage gate (normative, v0)

Allelic fork и старт AiNet **разрешены**, когда von-neumann одновременно:

1. **Dialogue parity** — held-out situation chains (0057): repair, mentalizing, math у доски на уровне **lab teacher** (Cursor-class interlocutor), не green-block isolation.
2. **Zone separation proven** — tract/core deltas наблюдаемы по зонам (social ≠ linguistic ≠ logical) на probe ladder.
3. **Persistence** — переживает sleep-merge + N тиков без tabula rasa; character EMA + journal continuity.
4. **Metabolic stability** — нет hang; forced_sleep восстанавливает, не ломает store.

До gate: `fork_policy.mode = inherit_verbatim`, `mutation_policy.allelic.enabled_on_fork = false`, **no** Hamilton/Lovelace spawn.

#### AiNet — не «следующий агент», а среда

AiNet имеет смысл, когда есть **другой субъект того же класса** — peer для диалога, обмена deltas и отбора lineage. Один Neumann + KB — лаборатория; **два и более** persisting agents + канон — **AiNet**.

Lab teacher (Cursor / operator) в gate — **эталон parity**, не член рода. Hamilton / Lovelace — **члены рода** `casa.von-neumann.ru-v1`, рождаются **после** первенца, не вместо него.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| «Genome immutable» без различия contract / alleles | sealed contract + bounded allelic fork |
| Runtime surprise переписывает `surprise_gains` в genome | experiential drift в lattices; allelic только fork |
| NCA drift на каждом тике | drift только sleep-merge + policy σ |
| Fork меняет `allowed_zone_ids` | species fork + new ADR |
| Promote sandbox → core без θ | `promote_canon.sandbox_theta` из genome |
| Два инстанса, один `store_id` | child = new store + new hash |
| Fitness = один REPL ответ | probe ladder + metabolic stability (0057) |
| Budding / copy-paste store как «сестра» | allele fork + новая жизнь + parent passport (§8) |
| AiNet до peer-level Neumann | сначала gate §8, потом Intercom |
| Hamilton / Lovelace cold boot | только child fork от von-neumann |

---

## Consequences

- ADR-0062 **уточняется:** `immutable_after_seal` = **no agent hot-path writes**; allelic evolution — по 0065.
- ADR-0064 metabolic `forced_sleep` становится **разрешением** experiential mutation window, не произвольным shutdown.
- ADR-0061 sandbox/promote — **основной** Track A; genetic sandbox **по-прежнему нет** (аллели не экспериментируют внутри жизни).
- AiNet merge: experiential deltas OK; genome hash mismatch без `fork_policy` lineage → **reject**.
- Tests: `apply_allele_fork` respects bounds; drift disabled when `drift_requires_sleep` and no merge; invariant keys unchanged on mutate.
- **Lineage:** Hamilton / Lovelace + AiNet — **P8**, после lineage gate §8; budding явно anti-pattern.

## Links

- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md)
- [CASA-ADR-0064-metabolic-zone.md](CASA-ADR-0064-metabolic-zone.md)
- [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md)
- [CASA-ADR-0059-innate-organ-basis.md](CASA-ADR-0059-innate-organ-basis.md)
