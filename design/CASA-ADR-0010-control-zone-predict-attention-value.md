# CASA-ADR-0010: расширение управляющей зоны — Predict / Attention split / Value

**Статус:** proposed (design; mechanism-кирпич value→replay в `replay_buffer_v0`)  
**Дата:** 2026-05-31  
**Область:** control lattice stack (DMN/SN/FPN/CEN), predictive coding, sparse routing, prioritization  
**Вдохновение:** NVIDIA Cosmos (WFM: Predict / Transfer / Reason + Tokenizer / Guardrail) + крупномасштабные сети мозга (DMN, SN, **DAN/VAN**, лимбическая оценка, forward-model) — но **инженерно и эффективнее**, на одном CA-субстрате  
**Связано:** [`control-lattice-stack-v0.md`](control-lattice-stack-v0.md), [`casa-cosmos-mapping-v0.md`](casa-cosmos-mapping-v0.md), [`fpn-control-region-v0.md`](fpn-control-region-v0.md), [`understanding-contract-v0.md`](understanding-contract-v0.md), [`CASA-ADR-0009-experience-replay-retention.md`](CASA-ADR-0009-experience-replay-retention.md), [`modules-fmri-analogy-v0.md`](modules-fmri-analogy-v0.md), [`surface_error_v0.py`](../tools/surface_error_v0.py)

---

## Контекст

Сейчас управляющая зона = 4 решётки + мосты P1–P5:

```text
DMN(что знаем) ─P1─► SN(что релевантно) ─P2a─► FPN(какая задача) ─P2b─► CEN(что сделать) ─P3─► DMN
```

Два зафиксированных в каноне пробела:

1. **«Predict — нет».** [`fpn-control-region-v0.md`](fpn-control-region-v0.md) и [`casa-cosmos-mapping-v0.md`](casa-cosmos-mapping-v0.md) приравнивают Cosmos **Predict** к DMN+repair. Но DMN = «что знаем» (состояние мира), а Cosmos Predict = **rollout следующего состояния**. [`understanding-contract-v0.md`](understanding-contract-v0.md) настаивает: понимание — **постоянная внутренняя симуляция** («если сделаю X — ожидаю Y» → сравнить с реальностью → surprise). Сейчас это неявная петля, **не орган**.
2. **SN перегружен.** SN делает и **детект salience** (bottom-up), и **роутинг/gate**. В мозге это разные сети: **VAN** (реориентирование на стимул) vs **DAN** (top-down прожектор внимания по цели). Слияние мешает **разрежённой** активации (только нужные модули/шарды), хотя [`modules-fmri-analogy-v0.md`](modules-fmri-analogy-v0.md) уже намекает на «restrict rollout to active modules».

Плюс приоритизация (что усиливать, что реплеить на sleep) сейчас **слепая** (recency/FIFO) — нет органа ценности.

---

## Решение: +3 управляющие решётки (тот же паттерн «+1 узел, не resize»)

| lattice_id | Сеть мозга | Cosmos | Роль (инженерно) | z_phase tail |
|------------|-----------|--------|------------------|--------------|
| **`lattice_predict`** | forward-model (cerebellar/parietal) + DMN-симуляция | **Predict** (rollout) | из digest+цели прогнать NCA k шагов → **ожидаемый** next-digest; отдать prediction-error | encode→roll→digest |
| **`lattice_dan`** | DAN (dorsal attention) | часть Reason (план→внимание) | top-down **прожектор**: какие концепты/шарды/решётки амплифицировать на тик | gate(mask) |
| **`lattice_value`** | лимбическая оценка (vmPFC/striatum) | Guardrail/critic-reward | скалярный **тег ценности/приоритета** концепта/эпизода/правила | digest(scalar) |

**DMN остаётся** «что знаем»; **`lattice_predict`** — «что ожидаем дальше». Это и закрывает «Predict — нет», не ломая семантику DMN.

### Новые мосты (P6–P9, типизированные как control_bridge)

| bridge | from → to | Несёт |
|--------|-----------|--------|
| **P6** | FPN → DAN | цель/режим → top-down attention spotlight |
| **P7** | DAN → DMN / L2 / predict | sparse activation mask (что читать/катить) |
| **P8** | predict → SN | **prediction error** как bottom-up salience (surprise) |
| **P9** | value → SN / sleep / replay | bias gate + порядок консолидации + приоритет реплея |

### Контур как предиктивное кодирование на control-стеке

```text
        ┌───────────────── P8 prediction error ─────────────────┐
        ▼                                                        │
  SN(salience) ─P2a─► FPN ─P6─► DAN ─P7─► DMN/L2 (sparse read)   │
        ▲ P9                     │ P7                            │
        │                        ▼                               │
  VALUE                       PREDICT(rollout k) ────────────────┘
        │ P9 → replay/sleep priority (ADR-0009)
```

Артикуляция/act идёт **после** predict: агент сперва «прогоняет модель», сравнивает, при surprise → ASK/Extract; только потом говорит (контракт USE).

### Почему это эффективнее (инженерно, не «как мозг ради мозга»)

| Лом | Выигрыш |
|-----|---------|
| **Один NCA-rule на все решётки** | predict/DAN/value — **те же** локальные правила + windowed train, новый класс модели не нужен |
| **DAN spotlight = sparse compute** | катим NCA только по активным модулям/шардам, не по всему 64×64 (ускорение infer) |
| **value-weighted replay/sleep** | дешёвый скаляр превращает слепой FIFO в приоритет «по ценности × давности забывания» (ADR-0009) |
| **prediction error → surprise** | целевой сигнал для Extract/consolidation вместо эвристик; per-lattice repair сохраняется |
| **+1 решётка, не resize** | новый орган не перекраивает LTM/layout, как доказано на 64× L2 shards |

### Cosmos-паритет (обновление `casa-cosmos-mapping-v0`)

| Cosmos | Было (v0) | Станет |
|--------|-----------|--------|
| Predict | = DMN | **`lattice_predict`** (rollout), DMN = world-state |
| Reason | SN+CEN | SN(salience)+**DAN**(attention)+CEN(plan) |
| Tokenizer | (неявно codec) | `codec_grid_v0` как явный токенайзер поля |
| Guardrail | — | **`lattice_value`** + Critic + integrity-core |

---

## Обоснование (отклонённые альтернативы)

| Альтернатива | Почему нет |
|--------------|-----------|
| Оставить Predict внутри DMN | путает «знаю» и «ожидаю»; нет явного prediction-error для surprise |
| Расширять SN до внимания | перегруз одного органа; нет sparse spotlight; против fMRI-разделения |
| Внешний LLM как Predict | против UC (внешняя RAM, latency); Predict должен быть на поле |
| Один скаляр «понимание/важность» | смешивает surprise (predict) и value (limbic) — разные сигналы |
| Сразу мутировать `control-lattice-stack.v0.json` | сломает `init_control_lab`/bench до готового runtime; ниже — поэтапный план |

---

## Последствия / Roadmap

### Поэтапно (каждый шаг — green перед следующим)

- [ ] **R1 (design):** этот ADR; обновить `casa-cosmos-mapping-v0` (Predict→lattice_predict) и `control-lattice-stack-v0` (таблица lattice_id + P6–P9).
- [x] **R2 (value brick):** value-взвешенный replay в [`replay_buffer_v0.py`](../tools/replay_buffer_v0.py) (`value_weight`, тег value) + тесты — **первый кирпич `lattice_value`** без нового органа.
- [ ] **R3 (predict):** `lattice_predict` в `control-lattice-stack.v0.json`; `predict_tick_v0` (rollout digest) + `bench_predict_error_v0` (predicted vs observed). Reuse `train_sss_nca_v0 --lattice-id lattice_predict`.
- [ ] **R4 (attention split):** `lattice_dan` + P6/P7; sparse rollout mask из spotlight; SN сужается до salience+P8.
- [ ] **R5 (value organ):** `lattice_value` на поле + P9 в SN gate и в sleep-порядок; источники value: повторный surprise (`surface_error_v0`), teacher-emphasis, task-relevance из FPN.

### Не меняется

- Hot path predict без сети; новые решётки — тот же CA-rule, per-lattice repair.
- DMN/SN/CEN/FPN семантика и P1–P5 сохраняются (только SN сужается при R4).
- ADR-0009 replay остаётся валиден; value лишь добавляет вес приоритета.

### Понимание-контракт

`lattice_predict` делает «постоянную внутреннюю симуляцию» **органом**, а не неявной петлёй — прямая реализация инварианта «понимание без predict — только архив». Связать с UC v0.5 (predictor) и UC v1.3 (COMPREHEND).

---

## Проверка (критерии)

- [ ] R3: `bench_predict_error_v0` — predicted next-digest ближе к observed, чем baseline (no-rollout)
- [ ] R4: sparse rollout по DAN-mask даёт тот же ответ при меньшем числе активных ячеек (latency↓)
- [x] R2: value_weight меняет порядок реплея (high-value раньше) при сохранении дефолтного поведения
- [ ] R5: high-value коррекции консолидируются/реплеятся раньше low-value под интерференцией (retention@N, ADR-0009)

---

## Связанные документы

| Документ | Роль |
|----------|------|
| [`control-lattice-stack-v0.md`](control-lattice-stack-v0.md) | базовый стек DMN/SN/FPN/CEN + bridges |
| [`casa-cosmos-mapping-v0.md`](casa-cosmos-mapping-v0.md) | Predict/Transfer/Reason ↔ CASA (обновить по R1) |
| [`understanding-contract-v0.md`](understanding-contract-v0.md) | predict-петля как инвариант понимания |
| [`CASA-ADR-0009-experience-replay-retention.md`](CASA-ADR-0009-experience-replay-retention.md) | value→приоритет replay/sleep |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v0 (proposed): +3 control-решётки (predict / dan / value), мосты P6–P9, Cosmos-паритет; кирпич value→replay реализован |
