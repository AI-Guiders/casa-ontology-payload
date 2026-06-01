# CASA-ADR-0025: Autonomous execution tier (software engine → specialized hardware)

**Статус:** черновик (обсуждение вариантов)  
**Дата:** 2026-06-01  
**Область:** автономный tick, hot path, NCA, persist, sleep job, будущий «движок под CASA»  
**Связано:** [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) (north-star, 4 темы), [`CASA-ADR-0023-sleep-scale-thin-first.md`](CASA-ADR-0023-sleep-scale-thin-first.md), [`CASA-ADR-0024-control-thalamus.md`](CASA-ADR-0024-control-thalamus.md), [`CASA-ADR-0019-control-multi-prism.md`](CASA-ADR-0019-control-multi-prism.md), [`CASA-ADR-0017-compact-persist.md`](CASA-ADR-0017-compact-persist.md), [`CASA-ADR-0020-ooad-domain-model.md`](CASA-ADR-0020-ooad-domain-model.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`layered-ca-pipeline.md`](layered-ca-pipeline.md), [`control-lattice-stack.md`](control-lattice-stack.md), [`casa-wake-sleep-concept.md`](casa-wake-sleep-concept.md)

**North-star:** исполнение (T0–T4) служит **теме 1 и 3** Constitution — эффективный автономный tick и Standalone; не заменяет педагогику и симбиоз (темы 2 и 4).

**Линия идей (non-mandate):** Toffoli & Margolus, *Cellular Automata Machines* — локальные правила, фазы, параллельные шаги **t** внутри слоя **z**. Forth в CAM — исторический **runtime симулятора**, не целевая технология CASA. См. обсуждение: узкая машина = **фиксированный dataflow tick**, не новый язык.

---

## Проблема

Цель — **реально быстрая автономия**: агент часами/сутками в замкнутом контуре (tick → relay → lattice update → hippo/surprise → редкий commit) **без** постоянного тяжёлого LLM и **без** того, чтобы один lab-job блокировал store.

Сегодня (lab, `ingest-ref-afan` и аналоги):

| Наблюдение | Следствие |
|------------|-----------|
| Sleep / merge — **I/O + один поток Python**, не GPU | Ускорение «кремнием под matmul» не поможет consolidate |
| Fat `field_state.json` + сотни `.ltm` | Автономия упирается в **persist**, не в «медленную КА на клетку» |
| Оркестрация — Python + JSON | GIL, alloc, parse на **каждом** macro tick **T** |
| LLM — отдельный класс задачи | Его выносит API/GPU/NPU; **не** входит в CASA Engine |

**Интуиция (верная):** при росте масштаба **универсальный стек** станет потолком; для sustained autonomy нужен слой исполнения **узко под CASA** (формат решётки, фазы, мосты, thalamus FSM, batched sleep DMA).

**Риск (верный):** ранняя ASIC/FPGA при **незамороженном ABI** — дорогой перепил; Forth как «второй язык проекта» — лишний мост, не железо.

---

## Термины

| Термин | Значение |
|--------|----------|
| **Macro tick `T`** | Один цикл жизни агента: input/surprise, control, опционально predict на content |
| **Micro-step `t`** | Итерации CA/NCA внутри `z_phase` на одной решётке |
| **Autonomous subset** | Подмножество операций, которые **должны** идти без LLM и без полной гидратации всех призм |
| **CASA Engine** | Процесс/библиотека с **фиксированным hot path** (ниже), host вызывает редко |
| **Host** | C#/Python: ingest, health, spawn, LLM, UI, миграции |
| **Параметры (weights)** | Обученные коэффициенты в `model.pt` / ONNX — **не** токены на решётке, **не** bundles, **не** «настройки промпта» LLM |

---

## Оркестрация — first-class (не «оверхэд вокруг модели»)

**Продукт CASA** — не «маленькая NCA вместо GPT», а **явное управление потоками** между призмами и состояниями.

| Слой | Роль | Параметры NN? |
|------|------|----------------|
| **Оркестрация** | router (куда за фактами), thalamus (что пропустить **сейчас**, arousal/bandwidth), hot, wake/sleep, preempt | **нет** — таблицы, токены, FSM |
| **Память на решётках** | `ltm/`, cells, hippo → sleep → strengthen | данные; repair — через NCA |
| **NCA** | локальный иммунитет поля после damage | **да** — `model.pt` на решётку |
| **LLM** | редкий cold path: план, язык | **да** — гигабайты, вне autonomous tick |

**«Overhead» в этом ADR** — только **инженерный**: ms и I/O на пути *реализации* tick (Python, JSON, fat checkpoint). **Не** означает «маршрутизация лишняя по замыслу».

**CASA Engine (T1)** ускоряет **носитель** оркестрации (thalamus → router → relay → persist), **не** заменяет её одной сетью. Multi-prism и open `kind` ([`CASA-ADR-0016`](CASA-ADR-0016-prism-domains-hot-router.md)) — **архитектурная ставка**, не раздувание.

```text
  Смысл агента                    Субстрат (ускоряем, не отменяем)
  ─────────────                   ─────────────────────────────────
  куда / когда / что пропустить   Engine: FSM + slab + dirty ltm
  что помнить на поле             sleep + hippo (ADR-0023)
  как чинить раскладку            NCA (ADR-0002), по одной решётке
  как сформулировать ответ        LLM или decode-ONNX stub (опционально)
```

---

## Масштаб весов NCA (не путать с оркестрацией)

| Артефакт | Порядок параметров | Примечание |
|----------|-------------------|------------|
| Один union `model.pt` (Exp J, lab) | **~1,3×10⁵** (`channel_n≈170`, `hidden≈192`) | транскрипт `0a0eac51-…`, ~0,5 MB |
| Один L2-шард SSS | **~10⁴–10⁵** | `P ≈ H·(4C+1)`, `C=K+6`, `hidden=96` |
| Сумма всех `nca/*/model.pt` в store | **~10⁶–10⁷** | 64+ L2/L3 шардов; на tick грузится **один** файл |
| Оркестрация (router/thalamus) | **0** весов | рост **правил и связей**, не matmul |

---

## Autonomous subset (v0 — что входит в «быстрый контур»)

Граница для профилирования и для будущего бинарного ABI:

```text
AUTONOMOUS (hot)
  thalamus_tick: arousal → bandwidth → relay masks     [ADR-0024]
  router_resolve: policy → target prism (table lookup)
  hot_context: prune / salience edges (bounded)
  hippo_append + soft_cap check
  content_predict stub OR lightweight scoring (no LLM)
  lattice: encode (deterministic) | repair (NCA) | digest | gate  [layered-ca]
  control_bridge: token copy по статической таблице портов
  sleep_batch: merge episode → strengthen (bounded batch)         [ADR-0023]
  compact_persist slice: active prism + dirty lattices only       [ADR-0017]

HOST (cold)
  listen / ingest corpus, remigrate L2/L3
  spawn prism, stack JSON, agent overlay
  full health_report, export_pack
  LLM plan / natural language
  train NCA checkpoints (offline)
```

**Инвариант:** всё в `AUTONOMOUS` должно иметь **верхнюю границу работы на один `T`** (или явный batch budget для sleep job).

---

## Варианты исполнения (T0 → T4)

Обсуждаемые tier'ы; **не** обязательная последовательность «все до T4», а ветвление по метрикам.

### T0 — Baseline (сейчас)

| | |
|--|--|
| **Что** | Python tools + `field_state.json` / `ltm/`, monolithic или batched sleep (ADR-0023 roadmap) |
| **Плюсы** | Быстрые итерации ADR, lab, отладка |
| **Минусы** | GIL, JSON, fat checkpoint; sleep I/O-bound |
| **Когда достаточно** | Lab ingest, proof ADR, store &lt; ~10k hippo, редкий autonomous mode |

### T1 — **CASA Autonomous Runtime** (software coprocessor) — **рекомендуемый следующий шаг**

| | |
|--|--|
| **Что** | Один native процесс или **C# library (AOT)** + тонкий Python host: бинарный `LatticeSlab`, tick scheduler, без `json.load` на hot path |
| **Состав** | Thalamus FSM, router table, hot prune, hippo queue in memory, **mmap** / append-only episode log, batched sleep как **coroutine** с yield |
| **Persist** | Thin checkpoint (ADR-0017); `.ltm` append по dirty mask; sleep пишет checkpoint **между батчами** |
| **NCA** | Вызов существующего CUDA/py через **C API** или prebuilt `model.pt` loader — repair остаётся GPU, но **оркестрация** не в Python |
| **Плюсы** | 5–20× на оркестрации типично; ABI можно менять без кремния; совпадает с OOA&D (`casa.domain`) |
| **Минусы** | Нужен freeze формата slab; два runtime (host + engine) |
| **Оценка усилий** | M: 2–4 недели на tick + thalamus + router без NCA; +NCA hook отдельно |

**Forth/CAM здесь:** только как образец **компактного цикла** (`T` → `lattice` → `z_phase` → `t`), не как язык.

### T2 — **Batched NCA appliance** (GPU / many-core, всё ещё software)

| | |
|--|--|
| **Что** | Движок ставит в очередь **N решёток × k шагов repair** одним kernel launch; host передаёт handles, не cells по JSON |
| **Когда** | Профиль показывает **&gt;40%** autonomous wall time в `z_phase=repair` при многих shards |
| **Плюсы** | Масштаб L2×64 + control stack без N×Python overhead |
| **Минусы** | VRAM, batching policy, сложнее отладка damage |
| **Связь** | ADR-0002 train pipeline; windowed CUDA уже в lab |

### T3 — **FPGA PoC** (узкий ускоритель)

| | |
|--|--|
| **Что** | PCIe card или SoC: **фиксированный** 32×32, int8/16 NCA step, соседство 3×3 или 5×5, DMA ring buffer; CPU — thalamus + router + persist |
| **Подходит для** | Микрошаги **t** при frozen weights; **не** для merge hippo, **не** для LLM |
| **Плюсы** | Ватт/шаг, детерминизм, latency |
| **Минусы** | Разработка прошивки, freeze весов, мало гибкости; sleep/IO остаётся на host |
| **Go** | T1 стабилен ≥6 мес, repair &gt;40%, есть бюджет FPGA + чёткий ops/s target |

### T4 — **ASIC / custom silicon** (долгий горизонт)

| | |
|--|--|
| **Что** | Tile: SRAM lattice + systolic neighbor + phase FSM; chip-to-chip для multi-shard |
| **Когда** | Продуктовый объём, frozen spec, T3 доказал ops/W |
| **Non-goal v0** | Не планировать до bar agent v1 (ADR-0022) и стабильного autonomous subset |

---

## Сравнение вариантов (одна таблица)

| Критерий | T0 Python | T1 Native engine | T2 GPU batch NCA | T3 FPGA | T4 ASIC |
|----------|-----------|------------------|------------------|---------|---------|
| Time to ship | — | **короткий** | средний | длинный | очень длинный |
| ABI гибкость | высокая | средняя | средняя | низкая | очень низкая |
| Помогает sleep I/O | косвенно (ADR-0023) | **да** (mmap, batch) | нет | нет | нет |
| Помогает tick/NCA | слабо | средне | **сильно** | сильно (только t) | сильно |
| LLM / ingest | host | host | host | host | host |
| Forth/CAM смысл | — | **метафора** | batch tiles | silicon CA | production CA tile |

---

## Целевая архитектура (T1 — reference)

```text
┌─────────────────────────────────────────────────────────────┐
│ HOST (Python / C#) — cold                                   │
│  ingest, spawn, LLM, train NCA, health, migrate, UI          │
└───────────────────────────┬─────────────────────────────────┘
                            │ IPC: TickCommand / SleepBatch / LoadSlab
┌───────────────────────────▼─────────────────────────────────┐
│ CASA Engine (native, single-threaded event loop + IO threads) │
│  Scheduler: preempt sleep job if WakeTick                     │
│  ├─ ThalamusUnit    (arousal, bandwidth, relay)               │
│  ├─ RouterUnit      (static routes)                           │
│  ├─ HotUnit         (bounded edges)                           │
│  ├─ HippoUnit       (ring buffer episodes)                    │
│  ├─ LatticeUnit     (slab 32×32, z_phase FSM)                 │
│  ├─ NcaBackend      (T1: dlopen CUDA | T2: batched queue)    │
│  └─ PersistUnit     (dirty mask → ltm/, thin ckpt)            │
└─────────────────────────────────────────────────────────────┘
```

**Оси CAM (design only):** на LatticeUnit — внутренний цикл `for t in 0..T_phase: apply(rule[z_phase])`; между решётками — не CA, а **bridge** (копирование токенов по портам).

---

## Бинарный slab (черновик ABI для T1)

Чтобы обсуждать freeze:

| Поле | Тип | Примечание |
|------|-----|------------|
| `magic` | `CASA1` | |
| `lattice_id` | u16 hash / table id | |
| `w, h` | u8 (=32 v0) | |
| `z_phase` | u8 | encode/repair/digest/gate |
| `cells` | `uint16[token_id]` × w×h | или sparse RLE v1 |
| `dirty` | bitmask | persist только dirty |

JSON `field_state` остаётся **import/export**, не hot path.

---

## Go / no-go (метрики — снять до T2/T3)

Профиль **одного** representative store (напр. post–thin-first afan) на сценарии «1000 autonomous ticks без LLM»:

| Метрика | Порог «остаёмся T1» | Порог «смотрим T2» | Порог «смотрим T3» |
|---------|---------------------|--------------------|--------------------|
| % wall в `repair`/NCA | &lt;25% | **≥40%** | ≥40% + ops/s известен |
| % wall в JSON/persist | **≥50%** → сначала ADR-0017/0023 | &lt;20% после T1 | — |
| % wall в router/thalamus/hot | &lt;15% | — | — |
| p99 tick latency (ms) | цель &lt;50 ms lab | &lt;10 ms | &lt;1 ms на phase t |
| ABI changes / квартал | &gt;2 крупных | ≤1 | **0** (freeze) |

**No-go на железо (T3/T4):** autonomous subset не задокументирован; нет стабильного slab ≥6 мес; доминирует I/O sleep (лечится батчами, не FPGA).

---

## Вытеснение и автономия (связь ADR-0023 / 0024)

| Механизм | T0 | T1+ |
|----------|----|-----|
| Sleep job | monolithic / batched Python | **SleepJob** в Engine с `yield` + checkpoint |
| Wake tick | блокируется долгим sleep | **preempt**: `TickCommand` с priority над `SleepBatch` |
| Thalamus `band.quiescent` | metadata | Engine **не стартует** новый sleep batch |

---

## Roadmap (предложение)

| Id | Шаг | Tier | Зависимости |
|----|-----|------|-------------|
| E0 | Зафиксировать **autonomous subset** (этот ADR) + checklist в health | doc | — |
| E1 | Профиль: 1k ticks, разбивка % по подсистемам | measure | thin checkpoint желателен |
| E2 | `LatticeSlab` + round-trip import/export из `field_state` | T1 | ADR-0020 domain |
| E3 | `casa_engine tick` CLI: thalamus → router → relay (без NCA) | T1 | ADR-0024 |
| E4 | Hippo ring + batched sleep в Engine | T1 | ADR-0023 R1/R2 |
| E5 | NCA backend hook (single lattice repair) | T1+T2 | ADR-0002 |
| E6 | Batched multi-lattice repair queue | T2 | E5, метрики |
| E7 | FPGA spec (32×32 int8, DMA) — **только документ** | T3 | E6 + 6 мес stable ABI |
| E8 | ASIC — **не планировать** в agent v1 | T4 | продукт |

---

## Решение (пока черновик)

1. **Принять** цель: автономия = **CASA Engine** (T1), ускоряющий **оркестрацию + persist**; не Forth и не ASIC сейчас.  
2. **Отложить** T3/T4 до метрик и freeze ABI.  
3. **Параллельно** не ждать Engine: ADR-0023 thin-first + batched sleep на T0 (снимает I/O потолок).  
4. **CAM/Forth** — ссылка в [`layered-ca-pipeline.md`](layered-ca-pipeline.md) / этот ADR как **геометрия (z, t, T)**, не стек.
5. **Runtime T1 (предварительно):** **C# 14 + NativeAOT** в экосистеме Financial — не отдельный Rust/C++ `casa-engine`, пока нет требования «zero .NET» на устройстве.

---

## Выбор runtime: C# NativeAOT vs Rust/C++

| Критерий | **C# NativeAOT** (предпочтение) | Rust/C++ greenfield |
|----------|--------------------------------|---------------------|
| Roslyn, ADR-0020, Financial | один toolchain, рефакторинг | дублирование domain |
| Lab Python | тонкий host (`python` → P/Invoke / CLI) | FFI / gRPC |
| Cold latency | **лаб: ~0.7 ms** ONNX load+run (см. ниже) | сопоставимо, но новый CI |
| ONNX / малая модель на tick | `Microsoft.ML.OnnxRuntime` уже в стеке | ort crate / C API |
| NCA CUDA | P/Invoke / subprocess к PyTorch lab | отдельный мост |
| Когда Rust/C++ | — | embedded без CLR, или команда только systems |

**Лабораторный замер (2026-06, не бенчмарк Engine):** NativeAOT, **cold start** — импорт ONNX + обвязка inference **~0.7 ms**; модель **единицы МБ**, целиком в RAM/VRAM без проблем. По сути в тесте — в основном **decode** (готовые эмбеддинги / узкий head), не полный encode+decode как у LLM; decode **быстрый по природе**, не «магия AOT». Сравнение с **Qwen3.5-Coder-7B через Ollama** — другой класс: **гигабайты** весов, **не влезает на GPU целиком** (наблюдение lab: ~20% GPU / 80% CPU), latency **секунды+**, не ms.  
**Оговорка:** замер **до** полной **multi-prism** оркестрации (router, thalamus, N призм) — после неё overhead tick вырастет; нужен повторный профиль на representative store.  
**Вывод:** малая ONNX в Engine — кандидат на **autonomous predict stub**; Qwen — **cold path** (план, язык), не конкурент по ms.  
**Не путать:** 0.7 ms ≠ полный `TickCommand` (thalamus + slab + persist + multi-prism dispatch).

**Rust/C++** оставить как **escape hatch** (ADR E7-level), не как v1.

---

## Открытые вопросы (для обсуждения)

1. ~~**Первый host Engine:** C# NativeAOT vs Rust?~~ → **склонность: NativeAOT** (§ выше); уточнить: отдельный `Casa.Engine` project vs библиотека в Financial.  
2. **Один процесс vs sidecar:** Engine как DLL в agent process или subprocess с shared memory?  
3. **Predict на autonomous tick:** отключён, stub, или маленькая локальная модель (не LLM)?  
4. **Sparse cells:** сразу RLE в slab или плотный `uint16` для v0?  
5. **Multi-store:** один Engine на machine или engine per `store-dir`?

---

## Non-goals

- Переписать весь CASA на Forth.  
- ASIC/FPGA в agent v1 bar.  
- Ускорять LLM inference «кастомным чипом CASA».  
- Заменить domain model (ADR-0020) — Engine **реализует** domain, не дублирует ad-hoc.
- Свести агента к **одному** `model.pt` / одной LLM — оркестрация и multi-prism остаются нормой.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | Черновик ADR-0025: варианты T0–T4, autonomous subset, go/no-go, roadmap E0–E8 |
| 2026-06-01 | § NativeAOT vs Rust; лаб ~0.7 ms ONNX cold; предпочтение C# T1 |
| 2026-06-01 | § Оркестрация first-class; масштаб NCA vs веса; non-goal «одна сеть» |
| 2026-06-01 | Ссылка на [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) |
