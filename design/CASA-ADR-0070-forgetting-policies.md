# ADR-0070: Политики забывания (decay и удержание в Memory Zone)

**Status:** proposed (черновик)  
**Date:** 2026-06-08  
**Related:** ADR-0068 (Memory Zone), ADR-0069 (Immutable), ADR-0058 (Limbic affect), ADR-0060 (Emotional zone), ADR-0062 (Genetic zone), ADR-0065 (Controlled mutations), ADR-0064 (Metabolic Zone), ADR-0066 (Neuromodulator), ADR-0010 (control stack / value), ADR-0055 (WM prism), ADR-0023 (sleep scale), [multi-cylinder-memory.md](multi-cylinder-memory.md), [prism-memory-architecture-v1.md](prism-memory-architecture-v1.md), [hippo-lattice-stack.md](hippo-lattice-stack.md)

---

## Context

**ADR-0068** зафиксировал три **memory kind** (explicit / implicit / immutable) и sleep consolidate **hippo → explicit semantic (mutable)**.

Обсуждение с оператором: субъекту нужен не один «механизм забывания», а **семейство политик** — что удерживать, что ослаблять, что вытеснять. Без этого:

- очередь episodic и hot context **раздуваются**;
- bind **интерферирует** (похожие эпизоды, устаревшие lemmas);
- sleep теряет смысл как **отбор**, а не копирование всего;
- immutable + растущий explicit дают **равный вес шума** в tract competition.

**Уже в design/code (фрагменты):**

| Механизм | Где | Kind |
|----------|-----|------|
| Priming decay halflife | manifest 0068 | implicit |
| WM `prune_wm_lattice`, θ_decay | ADR-0055 | explicit STM |
| Hippo trim post-consolidate | multi-cylinder, prism-memory | explicit episodic |
| `prune_hot_context` | prism-memory-architecture | hot scratch |
| Immutable no hot write | 0069 | immutable (удержание) |

**Пробел:** нет **единого ADR** — какие политики на какой kind, порядок на `T_sleep`, связь с **value** (0010), **metabolic** (0064) и emotional salience (0058).

**Orion v0 (2026-06-08):** предложена **физика забывания на трёх скоростях**, привязанная к трём классам стабильности поля — ниже как **операционный v0 spec** §1, согласованный с 0068/0069.

---

## Problem

| Без явных политик забывания | Риск |
|-----------------------------|------|
| «Помнить всё» | псевдо-бесконечная RAM, collapse bind budget |
| Удалять semantic как episodic | ломаем lexicon / curriculum |
| Забывать до consolidate | sleep бессмысленен; потеря repair chains |
| Забывать immutable | ломается опорный каркас; обход через drift |
| Один global TTL | social episodic ≠ math one-off; слепо к tract |

**Цель:** декларативная **матрица удержания** по memory kind + hooks на wake/sleep/tick; REPL / MEMORY.md показывают **что ослаблено / вытеснено** и почему.

---

## Decision (proposed)

### 1. Три скорости забывания (Orion v0 — физика)

Забывание в Memory Zone пульсирует на **трёх часовых масштабах**, привязанных к **фазе metabolic**, не к одному global TTL:

```text
[SYNC / TICK]        ──►  Скорость-1  затухание priming     (каждый tick)
[METABOLIC DEBIT]    ──►  Скорость-2  вымывание episodic    (каждые N ticks / load)
[SLEEP-MERGE]        ──►  Скорость-3  NCA erosion           (фаза сна)
```

| Скорость | Имя (Orion) | CASA kind (0068) | Триггер | v0 математика |
|----------|-------------|------------------|---------|---------------|
| **1** | микро-забывание | **implicit.priming** (+ WM activation) | каждый `T_wake` tick | `a[t+1] = α × a[t]`, **α = 0.2** (падение на 80% за tick); без повтора → ~0 |
| **2** | вымывание episodic | **explicit.episodic** | metabolic debit / каждые **N** ticks | проводимость → 0, если нет co-occurrence с semantic hub **и** load высокий |
| **3** | синаптический prune | **implicit.procedural** (веса NCA) | `T_sleep` по forced_sleep metabolic | **NCA erosion**: диффузия незакреплённых связей; закреплённые сохраняются |

**Три класса стабильности поля** (Orion ↔ CASA):

| Класс стабильности | Orion | CASA `memory_kind` | Коэффициент decay |
|--------------------|-------|-------------------|-------------------|
| **CANON_IMMUTABLE** | алфавит, ось KNOW, morph slots | **immutable** (0069) | **λ = 0** (нет затухания) |
| **Experiential** | journal, hippo, lexicon drift, гипотезы | **explicit** (+ WM scratch) | скорости 1–3 по subkind |
| **Agent canon** | earned postulates, promoted WM | immutable earned или explicit→promote | λ = 0 пока active; **demote** возвращает decay |

**Согласование с 0069:** Orion говорит «вечны, как гравитация» про CANON_IMMUTABLE — в CASA **операционно** то же (**λ = 0** на hot/sleep path). Эпистемически immutable = **принятые postulates**, не утверждение о физической вечности; смена теории = **theory fork / demote**, не erosion.

#### Скорость-1 — implicit.priming (микро-забывание @ tick)

- **Что:** недавний bind / активация рёбер WM, следы priming.
- **Когда:** `memory.priming_decay()` в начале tick hook (0068 §6).
- **Механика:** плоский экспоненциальный decay. Буква/токен вспыхнул на tick N → на N+1 activation × **0.2**; без повторного bind импульс исчезает, поле чисто под новый ввод.
- **Wire:** `forgetting.implicit.priming_alpha_retain: 0.2` (default в manifest; genetic может переопределить).

```text
activation[t+1] = priming_alpha_retain × activation[t]   # default 0.2
```

#### Скорость-2 — explicit.episodic (вымывание @ metabolic debit)

- **Что:** `journal/entries.jsonl`, hippo `episodic-*`, записи с `kind: "hypothesis"` без held-out pass.
- **Когда:** не каждый tick — на **metabolic debit** (surprise, compose, bind cost) и/или каждые **N** ticks при росте `autonomic.load`.
- **Механика:**
  - Metabolic Zone (0064): долгий wake → растут `fatigue_ema`, `sleep_pressure`, `regulatory_effort` (neuromodulator 0066).
  - Эпизоды **без** co-occurrence / близости embedding к **semantic hub** (active tract + WM core) плавно теряют проводимость → 0.
  - Освобождает `agent_field.db` / episodic store от балласта **до** sleep (не только trim post-merge).
- **Held-out gate:** гипотеза не подтверждена probe → ускоренное вымывание (boost скорости-2).

```text
episodic_weight[e] -= β × metabolic_load × (1 - hub_cooccurrence[e]) × Δticks
```

**v0 defaults:** `episodic_fade_every_n_ticks: 8`, `β` из genetic `forgetting.episodic` или metabolic policy.

#### Скорость-3 — implicit.procedural (NCA erosion @ sleep)

- **Что:** веса `nca/*/model.pt` на решётках 64×64 — procedural «магистрали».
- **Когда:** Metabolic Zone **forced_sleep** → фаза `T_sleep` merge.
- **Механика:** проход NCA **erosion** (лёгкая диффузия) по mutable procedural targets; связи **не** закреплённые сигналом **dopamine / success** (probe pass, repair success, `value` 0010) размываются.
- **Закреплённые:** рёбра, усиленные при успехе на wake, сохраняются; ~158 MB `nca/` остаётся чётким на инвариантах навыка.
- **Не трогает:** immutable lattices, explicit semantic shards (отдельный путь — semantic decay мягче).

```text
T_sleep:
  consolidate (hippo → explicit semantic)
  nca_erosion(strength=ε, mask=uncemented_edges)
  forget_episodic_trim
```

**v0 defaults:** `nca_erosion_epsilon: 0.02`, `cement_threshold` из probe pass / dopamine tick log.

#### Граница CANON_IMMUTABLE (жёсткий инвариант)

```text
∀ lattice WHERE memory_kind == immutable:
  λ_decay = 0
  Скорости 1/2/3 НЕ МОГУТ менять клетки поля или NCA на этих lattice_ids
```

Входит @ v0: `alphabet-*`, `syllables-ru`, `morph-role-*`, конвенции оси KNOW, таблицы keyboard/layout.

**Agent canon** (earned immutable): тот же λ = 0 пока **active**; **demote** (обратное promote_canon) возвращает lattice в explicit mutable + снова включает decay — только ceremony, не hot path.

**Только Experiential:** скорости 1–3 применимы. Explicit semantic decay — в основном скорость-2 (hub-cooccurrence) + semantic decay на sleep (§7), не полный NCA erosion.

---

### 2. Забывание ≠ одна операция

```text
forgetting
├── decay          ослабить strength / salience (восстановимо)
├── trim           убрать из active queue после успешного consolidate
├── archive        cold shard / digest в journal (не hot bind)
├── supersede      immutable: смена active_theory, lattice не удаляется
└── hard_delete    только operator / lab; never default hot path
```

**Invariant:** default path — **decay** или **trim**, не **hard_delete** на explicit semantic LTM.

### 3. Матрица удержания по memory kind

| Kind | Subkind | Удержание по умолчанию | Механизм забывания | Никогда |
|------|---------|------------------------|--------------------|---------|
| **immutable** | postulates | пока theory `active` | **supersede** @ theory fork; audit хранит lattice | hot decay, sleep merge overwrite |
| **explicit** | episodic | до consolidate или cap | **trim** hippo/dialogue post-sleep; salience floor | delete до попытки consolidate |
| **explicit** | semantic (mutable) | по strength | **decay** неактивных lemmas/edges; cold archive | wipe shard из-за одного bad turn |
| **implicit** | procedural | медленный EMA | **unlearn** ниже θ_skill; freeze при promote | стереть NCA из-за одной ошибки |
| **implicit** | priming | ticks | **скорость-1** decay каждый tick (α=0.2) | persist priming в LTM |

### 4. Wake path (T_wake)

```text
→ memory.priming_decay()              # скорость-1: implicit priming (α_retain=0.2)
→ metabolic_begin_tick / debit        # ATP, fatigue — ADR-0064
→ forget_episodic_fade? (every N)     # скорость-2: если load ↑, hub-cooccurrence
→ wm_prism.prune? (every N ticks)     # explicit STM — ADR-0055
→ prune_hot_context if over cap       # prism-memory-architecture
→ bind / compose
```

**Правило:** wake **не** hard-delete hippo; скорость-2 **ослабляет** проводимость; скорость-1 чистит priming/WM flash.

### 5. Sleep path (T_sleep) — consolidate, erode, trim

```text
T_sleep order (memory hooks):
  1. replay_queue / value sort (0010)     что консолидировать первым
  2. consolidate episodic → semantic      только mutable targets (0068)
  3. nca_erosion (скорость-3)             только незакреплённые procedural weights
  4. forget_episodic_trim                 hippo TTL, dialogue ring cap
  5. forget_semantic_decay                слабые / конфликтующие edges
  6. skip immutable (λ=0)                 CANON_IMMUTABLE (0069)
```

**Invariant:** **consolidate before trim** — episodic забывается только после merge attempt или явного `consolidate_skipped` (salience ниже θ).

```text
forget_episodic_trim(episode):
  IF episode.consolidated OR episode.salience < θ_episodic_floor:
    remove from hippo active queue
  ELSE:
    retain for next sleep (cap overflow → drop lowest salience)
```

### 6. Salience и закрепление (что сопротивляется забыванию)

| Сигнал | Влияет на | Источник |
|--------|-----------|----------|
| surprise / error | удержание episodic | tick, babble |
| emotional tag | скорость decay episodic + semantic | affect 0058 |
| repair success | дольше держим | dialogue |
| tract frequency | semantic decay медленнее | intent 0057 |
| value score (0010) | приоритет replay @ sleep | control stack |
| operator pin | без decay | manifest `retain_lattice_ids` |
| metabolic load | скорость-2 быстрее | metabolic 0064 `fatigue_ema` |
| hub co-occurrence | удержание скорости-2 | semantic hub / active tract |
| probe pass / dopamine | закрепление NCA edge (скорость-3) | neuromodulator 0066, held-out |
| гипотеза без verify | ускорение скорости-2 | journal `kind: hypothesis` |

**Формула (v0 sketch, не wired):**

```text
decay_rate(edge) = base_rate(kind) × (1 - emotional_salience) × (1 - tract_ema) × metabolic_load_factor
cement(edge)     = true IF probe_pass OR repair_success OR value_replay_selected
```

#### 6.1 Модуляторы коэффициентов: metabolic + limbic

Три скорости Ориона используют **базовые** α, β, ε из manifest/genetic; **эффективные** коэффициенты на каждом tick/sleep модулируются **metabolic** (интеграл усталости) и **limbic** (мгновенное состояние, 0058/0060):

```text
α_eff = α_base × f_arousal(arousal)                    # скорость-1 priming
β_eff = β_base × g_stress(fatigue_ema, valence, security)  # скорость-2 episodic
ε_eff = ε_base × h_consolidation(arousal, dopamine, sleep_depth)  # скорость-3 NCA
```

| Limbic / metabolic | Типичный эффект (гипотеза) |
|--------------------|----------------------------|
| Высокий arousal | быстрее чистится priming; сильные episodic держатся, слабые смываются |
| Низкий security / тревога | выше β_eff на нерелевантное; риск зацикливания на threat cues |
| Низкий arousal / скука | episodic блекнет быстрее; слабое cement @ sleep |
| Repair + positive valence | ниже β на tagged episodic; выше cement gain |
| `fatigue_ema` ↑ (0064) | β_eff ↑; триггер скорости-2 между sleep |

**Wire (target):**

```text
forgetting.modulators
  ├── metabolic_ref    fatigue_ema, sleep_pressure, regulatory_effort (0064, 0066)
  └── limbic_ref       valence, arousal, security, episodic_affect_tags (0058)
```

**API stub:** `affect_forgetting_gains(state) → {alpha_scale, beta_scale, epsilon_scale}` — вызывается перед применением скоростей 1–3.

**REPL (verbose):** показывать `α_eff, β_eff, ε_eff` рядом с counts — видно, *почему* в этом ходе забывание агрессивнее.

**Не путать:** лимбика **модулирует** experiential forgetting; не заменяет ceremony demote/promote для immutable.

### 7. Explicit semantic — только мягкое забывание

Lexicon / phrase shards:

| Действие | Когда |
|----------|-------|
| **decay strength** | lemma не использовалась N sleeps; tract idle |
| **merge duplicate** | политика sleep consolidate |
| **archive to cold** | shard over cap; operator opt-in |
| **hard delete** | только operator CLI |

**Anti-pattern:** удалить lemma из hot shard из-за одного OOV failure.

### 8. Immutable — CANON_IMMUTABLE @ healthy agent

**λ_immutable = 0** на experiential path (скорости 1–3) — контракт **здорового вида** @ teaching/REPL: alphabet, morph, KNOW-axis **не** размываются sleep/NCA/hot decay. Это **нормальная цена адаптивности**: experiential память пластична, postulate tier стабилен для bind.

| Событие | Политика (nominal / healthy) |
|---------|------------------------------|
| Hot path | **λ = 0** (скорости 1–3 выкл. на immutable) |
| Sleep | без merge в lattice, без NCA erosion |
| Theory fork | новая ветка; старый lattice `superseded_by`; **не** deleted |
| **Demote** | agent canon → explicit mutable; decay снова включён (ceremony) |
| Operator | revoke из **active** index (редко) |

«Забыть аксиому» в здоровом режиме = **demote** или **active_theory switch**, не erosion клеток.

#### 8.1 Патологическое забывание canon (genetic) — **draft, optional**

У людей **забывается и алфавит** — деменция, врождённые дефекты памяти, генетические заболевания, мутации. Архитектура **может** это моделировать отдельным каналом, **не** смешивая с experiential sleep merge:

```text
genetic_zone.forgetting_genotype          # 0062 / allelic 0065
  ├── canon_decay_floor                 0.0 @ healthy species default
  ├── episodic_retention_bias
  └── procedural_cement_gain

pathology_mode: none | dementia_sim | allelic_risk
  → λ_immutable_pathological > 0        только в этом режиме
  → медленная эрозия alphabet/morph (скорость-3-like, guarded)
```

| Механизм | Что | Инициатор |
|----------|-----|-----------|
| **demote / theory fork** | смена postulate | ceremony, agent/operator |
| **pathological decay** | размывание даже canon | genetic + chronic limbic stress + time |
| **allelic fork** (0065) | новая особь с другим genotype | species / operator |

**Probe в nominal mode:** `canon_immutable_touched == 0` (curriculum green).  
**В pathology sim:** отчёт `canon_immutable_touched: N (pathological)` — трагедия субъекта, не silent bug.

**→ см. Q7–Q8:** вводить ли в продукт вообще, или λ=0 forever — осознанная цена вида.

### 9. WM prism (0055) — полоса скорости-1 (агрессивная)

WM — **explicit STM** с агрессивным prune:

- edges `< θ_decay` → remove;
- lattice TTL / граница topic → promote или `delete_wm_lattice`;
- overload → freeze spawn, ускорить prune.

Консолидированное из WM → explicit semantic или journal; остальное **забывается по замыслу**.

### 10. State block (target)

```text
intelligence_zones.memory
├── …
├── forgetting
│   ├── speed_1_priming
│   │   ├── alpha_retain                 default 0.2 (Orion: −80%/tick)
│   │   └── apply_each_tick              true
│   ├── speed_2_episodic
│   │   ├── fade_every_n_ticks           default 8
│   │   ├── beta_fade                    metabolic-scaled
│   │   ├── hub_cooccurrence_min
│   │   ├── hypothesis_accel             true
│   │   ├── hippo_max_episodes
│   │   └── trim_after_consolidate
│   ├── speed_3_nca
│   │   ├── erosion_epsilon              default 0.02 @ sleep
│   │   ├── cement_from_probe_pass       true
│   │   └── skip_lattice_kinds           [immutable]
│   ├── semantic
│   │   ├── decay_halflife_sleeps
│   │   └── archive_shard_policy_ref
│   ├── modulators
│   │   ├── metabolic_ref
│   │   ├── limbic_ref
│   │   └── last_effective              { alpha_eff, beta_eff, epsilon_eff }
│   └── canon_boundary
│       ├── lambda_decay_immutable_nominal   0 (healthy default)
│       ├── lambda_decay_immutable_pathological  null | >0 @ pathology_mode
│       ├── pathology_mode                   none | dementia_sim | allelic_risk
│       ├── forgetting_genotype_ref          genetic_zone (0062)
│       └── demote_gate_ref                  genetic.demote_canon
└── consolidate
    └── last_forget_report_ref
```

**Чтение из других зон:** metabolic (0064), neuromodulator (0066), limbic (0058) → `modulators` → эффективные α, β, ε.

### 11. API (target: `casa/prisms/memory/forgetting.py`)

| Функция | Скорость | Когда | Роль |
|---------|----------|-------|------|
| `memory_priming_decay` | 1 | каждый tick | α_retain на priming + WM flash |
| `forget_episodic_fade` | 2 | каждые N ticks / metabolic debit | вымывание по hub-cooccurrence |
| `forget_episodic_trim` | 2 / sleep | post-sleep | cap hippo + dialogue |
| `nca_erosion_pass` | 3 | T_sleep | диффузия незакреплённого procedural |
| `forget_semantic_decay` | 2/3 | post-sleep | ослабление cold lemmas/edges |
| `forget_wm_prune` | 1 | tick | делегат 0055 |
| `forget_should_consolidate` | — | pre-sleep | salience + value gate |
| `forget_snapshot` | — | REPL | счётчики + `immutable_touched` MUST be 0 |
| `memory_retention_for_lattice` | — | catalog | λ=0 если immutable @ nominal |
| `affect_forgetting_gains` | — | pre-speed | limbic → alpha/beta/epsilon scale (0058) |

### 12. REPL / MEMORY.md (видимость)

Wake (verbose, опционально):

```text
forget_speed1: priming_cells_decayed=42
modulators: alpha_eff=0.18 beta_eff=0.31 (arousal=0.7 security=0.4)
metabolic: fatigue_ema=0.61 → episodic_fade_due=true
```

Отчёт sleep:

```text
forget:
  speed1_last_tick: priming_decayed=38
  modulators: alpha_eff=0.2 beta_eff=0.4 epsilon_eff=0.015
  speed2_faded: 7 episodic
  speed2_trimmed: 12
  speed3_nca_eroded: 1240 edges (cemented_kept=890)
  semantic_decayed: 47
  canon_immutable_touched: 0    ← MUST pass @ pathology_mode=none
  pathology_mode: none
```

**Existence north star:** память **дышит** — впитывает, сжимает, отсекает; забывание **видимо**.

### 13. Связь с 0068 / 0069 / metabolic

| ADR | Роль в забывании |
|-----|------------------|
| **0068** | ownership kind; порядок tick/sleep hooks |
| **0069** | CANON_IMMUTABLE λ=0; demote для agent canon |
| **0064** | metabolic debit → скорость-2; forced_sleep → скорость-3 |
| **0066** | regulatory_effort / dopamine как сигнал закрепления |
| **0058 / 0060** | limbic модулирует α_eff, β_eff, ε_eff |
| **0062 / 0065** | `forgetting_genotype`; allelic fork; pathology bounds |
| **0010** | value сортирует replay + приоритет cement |
| **0055** | WM — полоса скорости-1 |
| **0023** | thin checkpoint; batch перед trim @ scale |

---

## Open questions

### Q1 — Dialogue ring vs hippo

Одна политика trim или dialogue дольше для narrative continuity?

**Proposal:** dialogue ring — выше cap + archive в journal; hippo trim агрессивнее post-consolidate.

### Q2 — Semantic decay на lexicon 50k

Full-graph decay каждый sleep vs только tract-scoped?

**Proposal:** tract-scoped + global decay каждые K sleeps (perf).

### Q3 — «Забыл, но переучил»

Re-ingest той же lemma после decay — OK в explicit mutable; immutable promote только через ceremony.

### Q4 — Operator forget episode

CLI `forget_episode(id)` для repair pedagogy — P15?

### Q5 — Имя wire `regulatory_effort`

Orion: `autonomic.load`; в коде: `fatigue_ema` / `sleep_pressure` (0064). **Proposal:** alias в forget report; один metabolic input для скорости-2.

### Q6 — Ceremony demote_canon

Симметрия promote_canon для agent canon — genetic stub — P15g?

### Q7 — Патологическое забывание canon и роль генома

**Контекст:** люди разные от рождения; геном должен влиять на **все системы** (0062 §3), иначе fork бессмысленен. Forgetting — одна ветка, не весь геном.

| Решение (design direction) | |
|----------------------------|---|
| **Genome → все системы** | metabolic, affect, neuromodulator, tract proportions, forgetting_genotype, promote/demote — см. 0062 §3 |
| **Разнообразие @ fork** | `mutate_alleles` по нескольким группам → другой **голос** с tick 0 |
| **Teaching von-neumann** | standard allele; `canon_susceptibility ≈ 0`; общий bootstrap immutable |
| **Редкий аллель + chronic stress** | `canon_susceptibility > 0` + `pathology_mode` — lab / отдельная особь, не default curriculum |
| **Runtime erosion canon без genotype** | **anti-pattern** — иначе геном не при чём |

**Смысл размножения:** не «сломать alphabet», а **расхождение phenotype priors** при общем species scaffold.

### Q8 — Limbic модуляторы: v0 или отложить?

**Proposal:** v0 minimal — только metabolic на скорости-2; limbic scales (§6.1) — P16 после wiring affect на tick. Не блокирует P15a–f.

---

## Rollout (draft)

| Phase | Action |
|-------|--------|
| **P15a** | ADR-0070 accepted (Orion v0 speeds); manifest `forgetting` block |
| **P15b** | Скорость-1: `memory_priming_decay` α=0.2 @ tick |
| **P15c** | Скорость-2: `forget_episodic_fade` + metabolic load input |
| **P15d** | Скорость-3: `nca_erosion_pass` @ sleep + cement from probe |
| **P15e** | `forget_episodic_trim` post-sleep; hypothesis accel |
| **P15f** | `forget_snapshot`; probe `canon_immutable_touched == 0` |
| **P15g** | `demote_canon` genetic stub (только agent canon) |
| **P16** | `affect_forgetting_gains` + limbic modulators (§6.1) |
| **P17** | (Optional, Q7) `forgetting_genotype` + `pathology_mode` — только lab |

**v0 minimal vs Orion full:** P15b–f + nominal `λ=0` без §8.1; полный Orion + pathology — после закрытия Q7.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Один global TTL на всю память | Матрица удержания по kind |
| Delete semantic при failed bind | Decay strength; retry explicit |
| Trim hippo до consolidate | consolidate → then trim |
| Decay immutable @ healthy agent | λ=0 nominal; demote/supersede; pathology — отдельный режим (Q7) |
| Патология canon без `pathology_mode` | experiential erosion ≠ dementia sim |
| Limbic без отчёта modulators | показывать α_eff, β_eff, ε_eff в verbose |
| NCA erosion на alphabet/morph | `skip_lattice_kinds: [immutable]` |
| Тихое забывание | `forget_snapshot`; `canon_immutable_touched: 0` |
| Скорость-2 только @ sleep | metabolic fade каждые N ticks на wake |
| WM без prune | полоса prune/promote 0055 |
| Всё в MEMORY.md | Digest ≠ полное поле |

---

## Consequences

- Закрывает архитектурный зазор «память без вытеснения».
- Sleep = **consolidate + выборочное забывание**, не только merge.
- Immutable (0069) @ healthy agent — стабильный опорный каркас; experiential — **пластичная**.
- Limbic + genetic pathology — **optional** слой (§8.1, Q7); не обязателен для P15 minimal.

## Links

- [CASA-ADR-0058-limbic-affect-prism-v1.md](CASA-ADR-0058-limbic-affect-prism-v1.md)
- [CASA-ADR-0060-emotional-zone-v1.md](CASA-ADR-0060-emotional-zone-v1.md)
- [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md)
- [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md)
- [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md)
- [CASA-ADR-0069-immutable-memory-kind.md](CASA-ADR-0069-immutable-memory-kind.md)
- [CASA-ADR-0064-metabolic-zone.md](CASA-ADR-0064-metabolic-zone.md)
- [CASA-ADR-0066-neuromodulator-zone.md](CASA-ADR-0066-neuromodulator-zone.md)
- [CASA-ADR-0055-working-memory-prism-v1.md](CASA-ADR-0055-working-memory-prism-v1.md)
- [multi-cylinder-memory.md](multi-cylinder-memory.md)
- [prism-memory-architecture-v1.md](prism-memory-architecture-v1.md)
- [agent-existence-north-star.md](agent-existence-north-star.md)
