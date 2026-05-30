# Understanding contract v0 — смысл на поле, не RAG

**Статус:** design draft (контракт понимания; реализация v1+)  
**Дата:** 2026-05-30  
**Родитель:** [`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md)  
**Соседи:** [`hippo-lattice-stack-v0.md`](hippo-lattice-stack-v0.md), [`f0-math-logical-layer-v0.md`](f0-math-logical-layer-v0.md), [`predictor-v0.md`](predictor-v0.md), [`critic-v0.md`](critic-v0.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md)  
**KB (эпистемика, канон):** `knowledge/worlds/knowledge-engineering/playbook-epistemic-methods-and-calibration-v1.md` — `epistemic-hpmor-heuristics-v1`, `epistemic-methodology-v1`; L0 `epistemic-default-distrust-v1`

---

## Одна строка

**Понимание** — когда после explain / correct / направить агент на **held-out** ситуации **стабильно ведёт себя правильно**, опираясь **только** на структуру поля (digest, decode, hub), а не на `claim.text` / grep по bundle.

**И ещё:** понимание — не только «пережил сбой», а **постоянная внутренняя симуляция**: поле порождает ожидание → реальность его проверяет → расхождение консолидируется в структуру.

Provenance (`concept_id`, `doc_path`, git-KB) — **аудит снаружи hot path**, не генератор ответа.

---

## Что понимание **не** есть

| Артефакт | Почему не понимание |
|----------|---------------------|
| `claims_nav` + `compose_answer_text(claim.text)` | библиотечный поиск |
| ConceptCard / `explain_concept` для пользователя | педагогика **наружу**, не структура **внутри** |
| Высокий recovery NCA | помнит **раскладку** токенов, не **правило**; repair ≠ predict |
| NCA только как «иммунитет» | восстановление после damage — **реактивно**; мышление — **проактивная** симуляция (см. § ниже) |
| paste_ratio на **тех же** фразах из KB | подражание канону |
| LLM на hot path | внешняя RAM, не поле |

См. deferred [`articulation-explain-concept-v0.md`](articulation-explain-concept-v0.md).

---

## Predictive cognition vs NCA repair (ключевая ось)

Одна из **центральных** особенностей мышления — не только восстановление после сбоев, а **постоянное применение** имеющихся знаний: построить внутреннюю модель «что должно произойти, если…», сравнить **ожидание / реальность**, адаптироваться к новой ситуации. Мозг **симулирует реальность внутри себя** — не ждёт поломки.

В CASA это **два ортогональных контура** на **одном CA-субстрате** (решётка + локальное правило NCA). Не два разных «мозга».

### На CA? Да

| Слой | Роль на CA | Аналог |
|------|------------|--------|
| **Решётка + `ltm/`** | где лежат `C:`, `W:`, `R:`, `E:`, `M:` — **карта мира** | long-term memory / schema |
| **NCA (локальное правило)** | k шагов CA: соседи → новое состояние ячеек | **физика поля**, не энциклопедия |
| **decode + digest** | чтение активных токенов и hub после шагов | «что сейчас в модели активно» |
| **babble / compose** | генерация **гипотезы** из digest | forward pass / internal simulation |
| **surprise** | `hypothesis` ≠ observation (teacher, held-out, internal verify) | prediction error |
| **hippo → sleep** | episodic + merge в memory | belief update |

**NCA repair** (после damage patch) — **гомеостаз**: «ткань поля цела, раскладка восстановлена».  
**Predictive loop** — **кognition**: «если я понял правило — **должно** получиться X» → проверка → Extract при mismatch.

Оба используют **те же** решётки и то же локальное правило CA. Отличие — **цель шага**:

```text
  REPAIR (реактивно)          PREDICT (проактивно)
  ─────────────────          ────────────────────
  patch cells → NCA k steps   cue → encode → NCA k steps
  → layout ≈ target           → decode → digest → babble (= ожидание Y)
  метрика: recovery           метрика: Y vs reality / held-out
```

Внешний LLM на hot path **не нужен** для симуляции: «модель мира» = **структура на grid** + **динамика CA** + **decode**. Цитата из KB — cold path.

### Петля на каждом осмысленном тике (целевое)

```text
  digest (модель сейчас)
       │
       ▼
  PREDICT ──► babble / compose / segment_hypothesis
       │         («если сделаю X — ожидаю Y»)
       ▼
  ACT или OBSERVE ──► utterance учителя / held-out / env
       │
       ▼
  COMPARE ──► hypothesis vs target
       │
   match │ mismatch (surprise)
       │      │
       │      ▼
       │   ASK (CEN clarify) или Extract → hippo
       │      │
       └──────┴──► sleep → memory обновлена → следующий predict точнее
```

**Постоянство:** не только «один раз после explain», а **на новых cues** — прогон имеющихся `R:`, `E:`, `M:` через predict (фоновый self-test или перед act). Held-out bench — внешняя проверка той же петли.

### Lab сегодня (зачатки)

| Компонент | Файл | Что делает |
|-----------|------|------------|
| hypothesis → verify | `tools/sss_hypothesis_v0.py` | сегмент-гипотеза, verify, reconcile |
| multi-hypothesis | `tools/sss_field_hypotheses_v0.py` | конкуренция `H:{word}/{segment}` на hippo |
| UnderstandingUnit | § ниже | поля `hypothesis` / `target` |
| COMPREHEND | § «Эпистемический контур» | predict → validate → ask → extract |

**Не реализовано:** predict как **обязательный** шаг hot path перед act; surprise → CEN `clarify` без fallback на RAG.

### Инвариант контракта

> **Repair** сохраняет **носитель** знания (grid). **Predict** проверяет и **обновляет** знание (структура + episodic). Понимание без predict — только архив, не мышление.

### Два NCA repair на CA (одна математика, разные полки)

ADR-0002 фиксирует **NCA repair** на полках lexicon. Для **правил** — **тот же** механизм (damage → regrow), но **другая полка** и **другой gate на обучение**: только паттерны, которые Predict вывел и **Critic** подтвердил.

**Почему NCA на правилах:** правило на grid — тоже **раскладка** (`R:`, `E:`, cue→target на patch). При повреждении поля правило **должно восстанавливаться**, как слово на L2. Иначе predict/decoding ломается не только на лексиконе, но и на **выведенной структуре правила**.

```text
  PREDICT ──► гипотеза Y
       │
       ▼
  CRITIC ──► pass │ fail
       │ pass only
       ▼
  EXTRACT + REMEMBER
       ├── ltm/ + grid  (canonical layout правила)
       └── train NCA_rule  (regrow этого layout после damage — как repair на L2)
```

| NCA | Полка / patch | Target для обучения | Loss (тот же класс) |
|-----|---------------|---------------------|---------------------|
| **`NCA_repair`** | `L0…L3`, `L2_word_XX` | раскладка лексикона после listen/remigrate | patch damage → **regrow** `[K,H,W]` |
| **`NCA_rule`** | `H2_rule`, `L3_phrase` (rule region), `F2` compose patch | **только** snapshot после **Critic pass** | patch damage → **regrow** validated rule patch |

**Один и тот же CA:** локальное правило NCA, BPTT, windowed defaults — см. `nca-train-defaults.v0.json`. Различие — **не формула**, а **что** считается таргетом и **когда** разрешено обучать:

| | Lexicon repair | Rule repair |
|--|----------------|-------------|
| **Таргет** | полка после corpus/listen | patch правила после validate |
| **Gate** | remigrate / ingest | **Critic pass** (без pass — не train) |
| **Путь** | `nca/L2_word_07/model.pt` | `nca/rules/<rule_id>/model.pt` |

**Критик** — VALIDATE (SN + operational checks, § COMPREHEND). Fail → ASK / discard; **без pass — нет ни ltm-promote rule-NCA, ни snapshot для regrow.**

**Зачем и `ltm/`, и `NCA_rule`?**

| Носитель | Роль |
|----------|------|
| **`ltm/` + tokens** | **канон раскладки** правила на grid (sparse placements) |
| **`NCA_rule`** | **устойчивость** этой раскладки: после damage на patch — k шагов CA → layout ≈ validated target |

На hot path: decode повреждённого rule-patch → **`NCA_rule` regrow** → decode → predict/babble. Lexicon и rule **не смешиваются** в одном `model.pt`: разные полки, разные веса, **один** repair-алгоритм.

**Sleep pipeline (целевое v1):**

```text
critic_pass(unit) →
  merge R:, E: to memory ( _strengthen_rule )
  export rule patch to ltm (tier rule)
  snapshot [K,H,W] validated patch
  train nca/rules/<rule_id>/model.pt  (damage/regrow, windowed)
  pack.manifest.json: nca.rules[] + nca.models[]
```

**Lab сегодня:** `NCA_repair` на memory-полках; rule-patch repair + Critic gate — **UC v1.4**.

---

## Три обязательства контракта

```text
  EXTRACT (wake)     REMEMBER (sleep)      USE (act)
  ─────────────      ────────────────      ─────────
  среда → структура  hippo → memory       digest → babble
  на cyl_hippo       field_version++       без claim.text
                     ltm delta (opt.)
```

Каждый эпизод обучения должен пройти **все три**. Пропуск любого — не «понял», а артефакт пайплайна.

### 1. Extract (wake, T_wake)

**Вход:** utterance среды — текст учителя, dialogue, корпус, (roadmap) vis.

**Выход:** один или несколько **`UnderstandingUnit`** на **cyl_hippo** (не в markdown-KB как источник истины).

| Тип смысла | hippo lattice | Токены на grid | Пример |
|------------|---------------|----------------|--------|
| поверхность (форма) | **H1_surface** | `T:{ep_id}\|cue\|correct`, `C:{concept_id}` | «мама» → «маме» |
| правило / сегмент | **H2_rule** | `R:{rule_id}`, `E:{src}\|rel\|dst` | `ru.case.dative.after_soglasno` |
| сцена / turn | **H3_scene** | `T:…`, link tokens | диалог «кому? — маме» |
| логика (abstract) | **F1/F2** (roadmap) | `M:inst:*`, `M:qty:*`, hub `E:` | cow+cow → `M:qty:2×cow` |
| сырой listen | **H0_io** | promote или discard | буфер до оформления |

**Extract не копирует** абзац учебника в ячейку. Максимум — **короткий hint** в metadata эпизода (`rule_hint`) для человека; hot path читает **токены и рёбра**.

**API (целевое v1):**

```text
understand_extract(state, event) → UnderstandingUnit[]
  event.kind ∈ listen | babble_wrong | teacher_correct | teacher_explain
```

Сегодня частично: `append_episode`, `append_rule_episode` в `sss_cylinders_v0.py` → монолит `H0_episode`.

### 2. Remember (sleep, T_sleep)

**Вход:** очередь непроконсолидированных `UnderstandingUnit` (`H_replay_queue`).

**Выход:** изменения **cyl_memory** (+ опционально finetune NCA на затронутых tiles):

| Источник | Мост | Действие |
|----------|------|----------|
| H1_surface | `h_bridge_H1_L1`, `h_bridge_H1_L2` | `_strengthen_concept` — больше копий `C:` / `W:` на полке |
| H2_rule | `h_bridge_H2_L3` | `_strengthen_rule` — `R:{rule_id}` на L3 (+ hub edges roadmap) |
| H3_scene | `h_bridge_H3_L3` | bind phrase / context tokens |
| F1→F2 | `f_bridge_*` (roadmap) | quantity / compose на memory |

**Инварианты:**

- `field_version` на **memory** растёт только после успешного sleep-merge.
- Episodic TTL: consolidated episodes **prune** из hippo (не дублировать вечно).
- **ltm-pack export** v0 шипит memory-lattices; episodic — tier B/C ([`ltm-pack-v0.md`](ltm-pack-v0.md)).

Сегодня частично: `run_sleep` → `_strengthen_rule`, `_strengthen_concept`.

### 3. Use (act, любой T)

**Вход:** query / cue / context (новая формулировка, **held-out**).

**Выход:** babble, realize, compose — **только**:

```text
encode(cue) → [optional: NCA repair if damaged]
           → NCA k steps (field dynamics)
           → decode → digest
           → PREDICT: babble/compose (= внутреннее ожидание Y)
           → [compare Y vs cue/context if self-test]
           → SN → CEN → articulate(digest, field_slots)
```

На act-тике **PREDICT** может идти **до** articulation наружу: агент сначала «прогоняет модель», потом говорит / спрашивает.

**Запрещено на hot path (ablation off = pass):**

- чтение `claim.text` из bundle;
- `claims_nav` keyword match как генератор фразы;
- LLM completion как «понимание».

**Разрешено off-path:** provenance block в ответе для IDE («откуда взял concept_id»).

Сегодня частично: `bukvar_babble_v0.py`, `sss_babble_v0.py` — digest-only lepet; CEN/realize v0 **ещё** тянет claims.

---

## UnderstandingUnit (атом смысла на поле)

Аналог **claim** в KB, но носитель — **поле + episodic**, не markdown.

```json
{
  "schema_version": 1,
  "id": "u-20260530-abc",
  "kind": "rule",
  "hippo_lattice_id": "H2_rule",
  "cue": "согласно приказа",
  "hypothesis": "согласно приказа",
  "target": "согласно приказу",
  "anchors": {
    "concept_ids": ["lang.word.приказ", "ru.grammar.case.dative"],
    "rule_id": "ru.case.dative.after_soglasno",
    "edges": ["E:lang.word.согласно|gov|ru.grammar.case.dative"]
  },
  "grid_tokens": ["T:u-…|согласно|приказу", "R:ru.case.dative.after_soglasno"],
  "sleep_targets": ["L3_phrase", "L2_word_07"],
  "consolidated": false,
  "provenance": {
    "source": "teacher_correct",
    "doc_path": null
  }
}
```

| Поле | Назначение |
|------|------------|
| `kind` | surface \| rule \| scene \| compose (F0) |
| `anchors` | семантика для hub / SN, не текст ответа |
| `grid_tokens` | что реально лежит на hippo grid |
| `sleep_targets` | куда merge на T_sleep |
| `provenance` | аудит; **не** читается при articulate |

KB-claim может **зеркалиться** в git после sleep — как журнал, не как RAM агента.

---

## Hot path: контракт чтения

```text
┌─────────────────────────────────────────────────────────┐
│  HOT (понимание)          │  COLD (аудит / IDE)         │
├───────────────────────────┼───────────────────────────────┤
│  field_state / ltm→grid   │  bundle.json, git KB          │
│  NCA steps + repair       │  claim.text, ConceptCard      │
│  digest, decode, PREDICT  │  doc_path, section            │
│  hippo (wake only)        │  export reports, bench logs     │
└───────────────────────────┴───────────────────────────────┘
```

**Переключатель bench:** `claims_nav_enabled: false` — обязательный режим для метрики «понял».

---

## Критерий pass (bench v0)

**Имя (planned):** `bench_understanding_v0.py`

| # | Сценарий | Pass |
|---|----------|------|
| 1 | После 1–3 `teacher_correct` на train cues | на **held-out** cue форма из decode **matches** target (normalize) |
| 2 | Ablation | тот же pass при `claims_nav_enabled=false` |
| 3 | Damage | после N patches recovery + **тот же** ответ (память в структуре, не в prompt) |
| 4 | No paste | held-out **не** substring канонического claim.text |
| 5 | field_version | `field_version` вырос после session; sleep уменьшил hippo queue |

**Уровни понимания (не смешивать в одной цифре):**

| Уровень | Пример | Где проверять |
|---------|--------|---------------|
| **L-surface** | «маме» не «мама» | L1/L2 babble |
| **L-rule** | «согласно + D» → -у/-ю | L3 + `R:` |
| **L-scene** | тот же падеж в новом предложении | H3 → L3 |
| **L-logic** | 2×cow без слова «две» на F | F2 + hub |

---

## Сквозной пример: дательный после «согласно»

```text
1. LISTEN   «согласно приказу» в dialogue → encode L2/L3 (канон или corpus)
2. BABBLE   «согласно приказа» → wrong
3. CORRECT  teacher: «приказу, дательный после согласно»
            → Extract: H2_rule, R:ru.case.dative.after_soglasno
                       edge E:lang.word.согласно|gov|ru.grammar.case.dative
4. SLEEP    strengthen R: on L3; strengthen приказ/приказу on L2 shard
            field_version++
5. USE      cue: «согласно договору» (held-out)
            → decode активирует R: + dative cluster
            → babble: «согласно договору» (claims_nav OFF)
```

«Понял дательный» = шаг 5 без карточки «дательный — это…».

---

## Связь с F0 (абстракция)

Тот же контракт, другой `kind`:

| Шаг | Язык (L) | Логика (F) |
|-----|----------|------------|
| Extract | wrong segment | wrong compose (cow+cow≠2) |
| Remember | R: + L3 | M:qty:2×cow на F2 |
| Use | новое слово в том же падеже | новый `M:unit:*`, та же `M:op:add` |

Hub `E:lang.word.две|M:maps|M:qty:2×*` — мост второй сигнальности к первой ([`f0-math-logical-layer-v0.md`](f0-math-logical-layer-v0.md)).

---

## Эпистемический контур (как ГПиМРМ / HPMOR в KB)

**Идеал:** учитель объясняет **смысл** → агент **прогоняет через модель мира** (поле + digest) → **валидирует** → **спрашивает**, если не сходится → только потом **Extract → Remember → Use**.

Не «записал фразу учителя», а **belief update** с явной неуверенностью — тот же формат, что в каноне:

```text
heuristic → failure mode → operational check → revisit trigger
```

### Петля COMPREHEND (между listen и extract)

```text
  TEACHER_EXPLAIN (смысл, не цитата)
           │
           ▼
  ENCODE ──► digest + активные C:/E:/R:/M:  («модель мира сейчас»)
           │
           ▼
  PREDICT ──► babble / compose гипотезу («если понял — должно…»)
           │
     ┌─────┴─────┐
     │           │
  CONSISTENT   INCONSISTENT / LOW CONFIDENCE
     │           │
     │           ▼
     │      ASK (CEN: clarify / уточни)
     │           │  ← confusion = signal (HPMOR), не fake certainty
     │           ▼
     │      TEACHER answers → новый encode
     │           │
     └─────┬─────┘
           ▼
  VALIDATE ──► operational checks (см. таблицу)
           │
     pass │ fail → ASK или discard (не promote)
           ▼
  EXTRACT → hippo UnderstandingUnit
           ▼
  SLEEP → memory (Remember)
```

| Фаза | HPMOR / KB | CASA (целевое) |
|------|------------|----------------|
| **Модель мира** | map vs territory | digest + decode поля, **не** claim.text |
| **Гипотеза** | belief as probability | babble + `confidence` в SN |
| **Confusion** | pause, list unknowns | `gate.cen_open=clarify`, episodic H0_io |
| **Falsify** | prediction that can fail | held-out cue / internal mismatch |
| **Ask** | explicit disconfirming evidence | CEN `action: clarify`; articulation **вопроса** из digest |
| **Update** | revisit trigger met | sleep merge; `field_version++` |
| **Distrust** | L0 epistemic-default | не promote без pass validate |

### Operational checks перед Extract (v1)

Минимум **один** должен быть явным в `UnderstandingUnit.metadata`:

| Check | Pass | Fail → |
|-------|------|--------|
| **Coherence** | новый `E:` не противоречит сильным `E:` на поле | ASK или `kind=provisional` |
| **Coverage** | все concept_id из utterance есть или **emergent** помечен | ASK «что такое X?» |
| **Predict** | babble на paraphrase cue ближе к target, чем до explain | ещё один цикл ASK |
| **Boundary** | `transfer_boundary` заполнен (как KE card) | не sleep-merge в LTM |
| **Confidence** | SN mean_confidence ≥ θ или явный «не знаю» | ASK, не pretend |

**«Не понимаю»** — **валидный** исход hot path (lepет-вопрос из поля), не fallback на LLM/RAG.

### CEN modes (roadmap)

| mode | Когда |
|------|--------|
| `clarify` | validate fail / low confidence / contradiction на digest |
| `babble` | predict для self-test |
| `confirm` | coherent + high confidence → «понял так: …» учителю (optional) |
| `act` | после sleep + held-out pass |

### Связь с KB (cold path)

После успешного sleep — **опционально** mirror в git по KE pipeline (`Collect → Normalize → Promote`), формат как `epistemic-hpmor-heuristics-v1` или domain claim+edge.  
**Hot path агента на поле** не читает этот файл — только структура на grid.

### Пример: «лук — не только есть, но и стрелять»

```text
1. ENCODE utterance → digest: lang.word.лук + eat cluster (старое)
2. PREDICT: «лук — еда» (babble) — partial
3. INCONSISTENT с «стрелять» (нет edge / низкий score на action.shoot)
4. ASK: «лук стреляет — это шутка, игра, или буквально?»
5. TEACHER: «в игре / шутка» → boundary заполнен
6. VALIDATE: paraphrase «лук как оружие в игре» → digest согласован
7. EXTRACT: E:лук|affordance|action.shoot + scene + transfer_boundary
8. SLEEP → L3; USE на held-out без claims_nav
```

---

## Карта реализации

| Компонент | Сейчас (lab) | v1 контракт |
|-----------|--------------|-------------|
| Extract surface/rule | `append_episode`, `append_rule_episode` | `understand_extract`; shards H1/H2 |
| Remember | `run_sleep`, `_strengthen_*` | `H_replay_queue`, h_bridge table |
| Use digest-only | `bukvar_babble_v0`, `sss_babble_v0` | CEN/realize без claim.text |
| Self-correct loop | `sss_self_correct_session_v0.py` | + teacher_correct events |
| **Predict / hypothesis** | `sss_hypothesis_v0.py`, `sss_field_hypotheses_v0.py` | predict **обязателен** перед act; surprise → hippo |
| **Critic → NCA_rule** | — | `critic_pass(unit)`; `nca/rules/<rule_id>/` после validate |
| **Comprehend / validate / ask** | — | COMPREHEND loop; CEN `clarify`; confidence on SN |
| Listen → field | `sss_text_listen_field_v0.py` | без обязательного bundle ingest |
| Bench | read@1, paste, segment | **`bench_understanding_v0.py`** |
| Shipment | `ltm/` + `nca/` | runtime boot без `field_state.json` |
| F0 compose | design only | F1/F2 + bench_math_compose **после UC v0.5 predict** |
| **Predictor** | design [`predictor-v0.md`](predictor-v0.md) | `predictor_v0.py`, `bench_predict_v0.py` |
| **Critic** | design [`critic-v0.md`](critic-v0.md) | `critic_v0.py` gate before Extract / NCA_rule |

---

## Milestones

| Milestone | Deliverable |
|-----------|-------------|
| **UC v0.1** | ablation `claims_nav_enabled` в `cen_plan`; `store_boot_v0.py` (ltm-only); Exp L0 bench |
| **UC v0.2** | `bench_understanding_v0.py` на 10 held-out pairs (segment/dative) |
| **UC v0.5** | **`predictor_v0.py`** + **`bench_predict_v0`** (segment, schema); см. [`predictor-v0.md`](predictor-v0.md) |
| **UC v0.6** | **`critic_v0.py`** stub; predict→critic pass rate |
| **UC v1.0** | hot path articulate **только** digest; pass ablation на bench |
| **UC v1.1** | hippo H1/H2 split; migrate off `H0_episode` |
| **UC v1.2** | teacher_correct → UnderstandingUnit JSON schema stable |
| **UC v1.3** | COMPREHEND: predict → validate → CEN clarify (без claim.text) |
| **UC v1.4** | **Critic** gate stable; **NCA_rule** train on critic-pass patches; predict uses rule-NCA |
| **UC v2.0** | F0 compose в том же контракте (kind=compose) |

---

## Для агента (Cursor)

- Запрос «объясни падеж **мне**» → можно ответить человеку кратко.
- Задача «агент **сам** понимает» → реализовывать **Extract → Remember → Use**, не расширять ConceptCard.
- Любая новая фича articulation: проверить, не нарушает ли **hot path contract**.
- Перед «готово»: прогон bench с `claims_nav_enabled=false`.
