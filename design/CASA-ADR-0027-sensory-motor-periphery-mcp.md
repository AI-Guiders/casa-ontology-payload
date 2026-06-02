# CASA-ADR-0027: Сенсомоторный стек — периферия → адаптер → перцепция → мозг

**Статус:** черновик — **только обсуждение** (ничего ниже не «принято», пока мы явно не зафиксируем)  
**Дата:** 2026-06-02  
**Область:** как живой агент подключает глаза/уши/рот/руки к мозгу без LLM внутри `{store}/`  
**Связано:**

- [`CASA-ADR-0026-multimodal-event-ingest.md`](CASA-ADR-0026-multimodal-event-ingest.md) — **канон события** (`mm_event`, `mm_action`) — bootstrap ур.0–1
- [`CASA-ADR-0028-field-native-sensory-experience.md`](CASA-ADR-0028-field-native-sensory-experience.md) — **тракты** (primary/symbolic/efferent), ур. **2–3**
- [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) — один store, curriculum = события, не oracle на read
- [`CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md) — **FieldBus**, CU, codec vs substrate (CIDE parity)
- CIDE: ADR 0102 (DAL), 0094 (transport), 0097 (CCU), 0099 (DataBus) — `Financial/software/open/cascade-ide/docs/en/architecture/current-architecture-v1.md`
- [`CASA-ADR-0024-control-thalamus.md`](CASA-ADR-0024-control-thalamus.md) (вне payload) — маршрутизация внутри мозга
- [`CASA-ADR-0025-autonomous-execution-tier.md`](CASA-ADR-0025-autonomous-execution-tier.md) — host vs agent vs teacher vs lab
- [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) — LLM снаружи, не субстрат
- [`agents/README.md`](../agents/README.md) — зоны жизни / host / учитель

**Не дублирует 0026/0028:** 0026 = формат mm (bootstrap текст); 0028 = *какого типа* опыт в поле (ур.2–3); здесь — *доставка* до мозга и сменяемая периферия.

---

## Рабочая гипотеза (одной фразой) — *не финал*

**Цепочка:** `(Периферия) ↔ Адаптер ↔ Перцепция ↔ Мозг`.

- **Периферия** — любые устройства/сервисы (твои MCP, другой вендор, файл, симулятор).
- **Адаптер** (внутри host/CASA, **не** в `{store}/`) — единый внутренний контракт; подключает периферию без переписывания перцепции и мозга.
- **Перцепция** — ранняя обработка сырья → структурированный **percept** (текст, глифы, динамика, объекты); здесь допустимы ML (Whisper, OCR, CV).
- **Мозг** — `mm_event` / ingest / predict / sleep; **без** прямого доступа к камере и без привязки к MCP.

MCP — **одна реализация** периферии за адаптером, не архитектурный якорь.

**Укрупнённо — 4 слоя** (обсуждение с тобой). **Детально — как CIDE** (§ ниже): DAL → Transport → Perception → **CCU** → **FieldBus** → мозг (ingest + CU).

---

## Мотивация

| Вопрос | Ответ ADR |
|--------|-----------|
| «Нейманн смотрит как GPT-4o?» | **Нет.** Vision/ASR — орган; мозг получает дискретные события. |
| «Зачем MCP, а не всё в Python агента?» | MCP — сменный **драйвер периферии**; адаптер держит стабильный внутренний API. |
| «Чужая камера / другой ASR?» | Новый **адаптер** или новый **perception plugin**; мозг и `mm_event` не меняются. |
| «Cursor-агент с webcam MCP — это и есть Нейманн?» | **Нет.** Это оператор с протезами; relay делает то же без чата на каждом кадре. |
| «Почему не как CIDE (DAL / Bus / CU)?» | **Да, так и надо** — четыре слоя = сжатая карта; полный стек — § CIDE-aligned. |

---

## CIDE-aligned стек (расширение)

В CascadeIDE цепочка уже разложена ([`current-architecture-v1`](../../cascade-ide/docs/en/architecture/current-architecture-v1.md)):

```text
  DAL → Transport (0094) → CCU (0097) → DataBus (0099) → CDS / UI
```

В CASA для сенсомоторики + мозга — **та же логика**, другие имена и без UI-композитора:

```text
  ┌─────────── HOST (сенсорика) ───────────────────────────────────────────┐
  │                                                                         │
  │  [1] DAL          [2] SensoryTransport   [3] Perception    [4] CCU      │
  │  Adapter/         очередь / лог сессий,   plugins          свёртка в     │
  │  Codec backends   backpressure (0094)   (ASR,OCR,CV)    Percept/mm    │
  │       │                    │                  │               │         │
  │       └────────────────────┴──────────────────┴───────────────┘         │
  │                                    │ publish                            │
  │                                    ▼                                    │
  │                         [5] FieldBus (ADR-0012)                         │
  │              CaptureReady | PerceptReady | MmEventCommitted             │
  └────────────────────────────────────┬────────────────────────────────────┘
                                       │ subscribe (ingest handler)
                                       ▼
  ┌─────────── AGENT (мозг) ────────────────────────────────────────────────┐
  │  [6] Ingest / hippo / sleep / ltm          [7] CU — prism_control       │
  │      (substrate)                            predict, router, Kolb       │
  │  [8] Composition — store profile: какие призмы и pipelines смонтированы │
  │  [9] Orchestrator — sensory_loop + agent_wake + teacher inbox           │
  └─────────────────────────────────────────────────────────────────────────┘
```

### Таблица CIDE → CASA

| CIDE | Роль | CASA (сенсорика / мозг) | Где (целевое) |
|------|------|-------------------------|---------------|
| **DAL** (0102) | внешний I/O, MCP-клиент, fs, process | **Adapter + Codec** → `RawCapture` | `casa/sensory/adapters/`, `casa/sensory/codecs/` |
| **Transport** (0094) | доставка, буфер, backpressure | **SensoryTransport** — не блокировать capture на Whisper | `casa/sensory/transport/` |
| *(нет 1:1)* | ML/feature extract | **Perception** — плагины, параллельно | `casa/sensory/perception/` |
| **CCU** (0097) | raw/фичи → **DTO канала** | **PerceptCompositor** — окна, scene cuts, `percept_to_mm_event` | `casa/sensory/compositor/` |
| **DataBus** (0099) | typed pub/sub в процессе | **FieldBus** — границы фаз, не каждая клетка | `casa/field_bus/` (ADR-0012) |
| **CDS / surface** | кадр в UI | **Projections** (watchers, bench) или headless skip | lab, CascadeIDE panel |
| **Agent orchestrator** | шаг агента | **sensory_loop** + **TickOrchestrator** / `agent_wake` | `tools/`, `agent_life.py` |
| **Substrate** | Roslyn, git | **`field_state` + `ltm/`** | `agents/von-neumann/` |
| **CU** | вычислительный блок кабины | **prism_control** + NCA как ALU | ADR-0012 §2.3 |
| **Composition** | какие instruments в слоте | **store profile** + `backends.json` + perception pipeline id | manifest |

### Чем CCU ≠ Perception

| | **Perception** | **CCU (compositor)** |
|---|----------------|----------------------|
| Вход | `RawCapture` | выходы плагинов + transport meta |
| Делает | ASR, OCR, motion features | **один** снимок канала: слова, глифы, `window_ms`, нарезка по scene cut |
| Аналогия CIDE | куски DAL/внешних сервисов | **0097 fold** в channel DTO |
| Выход | промежуточные features | `PerceptPacket` / `mm_event` |

Сегодня `mm_build_event.py` — по смыслу **CCU**, а Whisper/OCR — **perception** (пока смешаны в MCP analyze).

### Чем FieldBus ≠ Transport

| | **SensoryTransport** (0094) | **FieldBus** (0099 / ADR-0012) |
|---|----------------------------|--------------------------------|
| Несёт | сырьё, job id, backpressure | **смысловые** события домена |
| Пример | `RawCapture` в очереди | `MmEventReady(ev)`, `IngestCompleted` |
| Подписчик | worker перцепции | ingest, metrics, `agent_wake` (лёгкий) |

**Правило из ADR-0012:** hot path NCA **не** на bus; bus — **границы фаз** (capture done, percept ready, sleep done).

### Codec (из ADR-0012)

Отдельно от DAL-адаптера: **wire/formats** (wav, jpg paths, jsonl session index) — `casa/sensory/codecs/`.  
DAL говорит с миром; codec знает, как упаковать/распаковать **файл сессии**, не как учить агента.

### Composition (что смонтировано)

Как CIDE `MainWindowHostSurfaceFrame`, у агента два уровня:

1. **Store profile** — `prism_visual`, `prism_auditory`, … (`CASA-ADR-0012`).
2. **Sensory profile** — какие `PeripheryCaptureBackend` и `PerceptionPipeline` активны:

```json
{
  "sensory_profile_id": "live-desk-v1",
  "capture_backend": "mcp_webcam_capture",
  "perception_pipeline": "hearing_whisper+vision_ocr_v1",
  "compositor": "mm_event_windowed_v1",
  "transport": "memory_queue_v1"
}
```

Смена камеры = правка `capture_backend`, не пересборка мозга.

---

## Слои (анатомия) — 4 слоя (укрупнённая карта)

```text
  ПЕРИФЕРИЯ     DAL/Adapter    Transport    Perception    CCU        FieldBus      МОЗГ
  MCP, файл  →  RawCapture  →  queue    →  ASR/OCR  →  mm_event → publish → ingest/CU
```

| Слой | Зона (ADR-0025) | Контракт (внутренний) | Смысл для агента? |
|------|-----------------|------------------------|-------------------|
| **Периферия** | вне agent store | vendor-specific (MCP JSON, IOCTL, …) | **Нет** |
| **Адаптер** | host (`casa/sensory/`) | `RawCapture`, `MotorSlot` | **Нет** — только нормализация IO |
| **Transport** | host | `RawCapture` jobs, backpressure | **Нет** |
| **Перцепция** | host | features (ASR, OCR, …) | **Нет** |
| **CCU / compositor** | host | `PerceptPacket` → `mm_event` | **Нет** — упаковка канала |
| **FieldBus** | agent process | typed events | **Нет** — шина, не память |
| **Мозг** | `agents/{id}/` | ingest + CU + life | **Да** — после sleep |
| Teacher inbox | teacher | lesson / mm jsonl | события по curriculum |
| Operator (Cursor) | lab | ручной вызов тех же слоёв | отладка |

**Граница «таламус»:** выход перцепции = **`mm_event` / `mm_action`** (канон ADR-0026). Всё левее таламуса — host; всё правее — агент.

---

## 1. Периферия (pluggable backends)

Физика и транспорт. Не знает про `field_state`, `mm_event`, призмы.

| Пример | Что отдаёт |
|--------|------------|
| `webcam-capture-mcp` | `session_dir`, frames, wav, sync meta |
| `webcam-analysis-mcp` | (если без адаптера — **антипаттерн**; лучше вызывать из perception) |
| File replay | те же поля из `lab/sensory/recording/` |
| Будущий SDK / ROS / другой MCP | то же по контракту адаптера |

---

## 2. Адаптер (внутренний, обязательный)

**Зачем:** чтобы Нейманн не был заложником «моих» MCP. Адаптер — тонкий слой **перевода**, без OCR/ASR.

### Сенсорный контракт (черновик v1)

```python
# casa/sensory/contracts.py — идея, не финальный API

@dataclass
class RawCapture:
    capture_id: str
    ts_ms: int
    session_dir: Path          # кадры, wav, metadata.json
    modalities_present: frozenset[str]  # {"video", "audio", "screen"}
    provenance: dict           # backend_id, mcp_server?, device_ids

class PeripheryCaptureBackend(Protocol):
    backend_id: str
    def capture_burst(self, *, duration_sec: float, ...) -> RawCapture: ...
```

Реализации адаптера (`casa/sensory/adapters/`):

| `backend_id` | Источник |
|--------------|----------|
| `mcp_webcam_capture` | вызов MCP `capture_av_burst` |
| `file_replay` | чтение готовой сессии (CI, регресс) |
| `stub` | синтетика для тестов |
| *(later)* `vendor_x` | чужой API без MCP |

### Моторный контракт (симметрия)

```python
class MotorCommand:
    action_id: str
    tts_units: list[dict]      # или другой motor encoding
    ...

class PeripheryMotorBackend(Protocol):
    def act(self, cmd: MotorCommand) -> MotorFeedback: ...  # wav path, device ack
```

**Правило:** адаптер **не** пишет в `agents/*` и **не** строит `canon.words`.

---

## 3. Перцепция (ранняя кора, host)

Берёт **`RawCapture`**, возвращает **`PerceptPacket`** или сразу **`mm_event`** (тонкий mapper).

| Этап | Примеры | Плагин |
|------|---------|--------|
| Слух | Whisper ASR, VAD, тишина/речь | `perception.hearing.whisper_v1` |
| Зрение (текст) | OCR batch | `perception.vision.ocr_v1` |
| Зрение (динамика) | scene cuts, motion | `perception.vision.dynamics_v1` |
| Зрение (объекты) | sticks/heaps CV | `perception.vision.objects_v*` (P4) |
| Сборка | ASR+OCR → words, math_glyphs, context | `perception.compose.mm_event_v1` |

Перцепция **может** внутри вызывать MCP analyze-tools — но только как **одну из реализаций** plugin, не как обязательный путь.

```python
@dataclass
class PerceptPacket:
    capture_id: str
    window_ms: int
    words: list[str]
    math_glyphs: list[str]
    punctuation: list[str]
    context_tags: list[str]
    dynamics: dict | None      # motion, scene_cuts — опционально
    objects: list[dict] | None # P4
    images: list[dict] | None  # provenance paths
    confidence: dict           # per-channel thresholds (ADR-0026 ASR)

class PerceptionPipeline(Protocol):
    pipeline_id: str
    def process(self, raw: RawCapture) -> list[PerceptPacket]: ...  # 1 raw → N windows
```

`PerceptPacket` → `mm_event`: функция **`percept_to_mm_event()`** (таламическая упаковка); логика сегодня в `mm_build_event.py` — переезжает сюда conceptually.

---

## 4. Мозг (agent store)

Без изменений относительно ADR-0021 / 0026:

- `ingest_mm_events` / teacher ingest → hippo → sleep → `ltm/`
- `agent_wake` / self_drive — **не** вызывают периферию в v1 (open Q1)
- `predict` читает только consolidated опыт

---

## Оркестратор host: `sensory_loop`

Один процесс (или ветка inbox-runner), **не** смешивая роли:

```text
  raw = adapter.capture_burst(...)
  for percept in perception.process(raw):
      ev = percept_to_mm_event(percept)
      append events.live.jsonl
  ingest_mm_events(...)   # мозг
  agent_wake(quanta=...)  # жизнь между окнами
```

| Шаг | Слой |
|-----|------|
| schedule / trigger | host |
| `capture_burst` | периферия ← адаптер |
| `process(raw)` | перцепция |
| `ingest` | мозг |

### Референс-склейка (сегодня → завтра)

| Сегодня | Слой после рефактора |
|---------|----------------------|
| `capture_*` MCP | периферия + `McpCaptureBackend` |
| `ocr_*`, `transcribe_*`, `analyze_av_*` MCP | перцепция (plugins) |
| `mm_build_event.py` | `percept_to_mm_event` |
| `ingest_mm_events.py` | мозг |
| `agent_inbox_runner.py` | оркестратор |

**Roadmap код:** `casa/sensory/adapters/`, `casa/sensory/perception/`, `tools/sensory_loop.py`.

---

## Граница канона (перцепция → мозг)

| На периферии (разрешено) | В мозге (после ingest) |
|--------------------------|-------------------------|
| Whisper, OCR, CV-детектор | `listen_scene`, L2/L3, `schema-math` episodes |
| Пути к файлам кадров в `mm_event.vision.images` | Ссылки как provenance, **не** embedding всего кадра в L2 |
| `analyze_av_sequence` — motion, scene cuts | Опционально `canon.context` теги: `motion:high`, `scene_cut` |
| Teacher feedback в `mm_action.world` | Эпизоды коррекции + sleep |

**Инвариант (наследие 0021):** на `predict` read path нет «подсказки из последнего OCR» — только consolidated опыт.

---

## Моторика (обратный канал)

Симметрия четырёх слоёв:

```text
  мозг: policy → mm_action
       → адаптер.motor.act(MotorCommand)
       → периферия (TTS / другое)
       → мир
       → периферия (микрофон) → RawCapture
       → перцепция (ASR) → percept heard_text
       → mm_action.world + reward → ingest → sleep
```

v1: моторика **вне** автономного `agent_self_tick` — инициируется teacher сценарием (Echo / Request / Label, ADR-0026). Спонтанная речь — только если в опыте есть reward-цепочка, не «LLM решил сказать».

---

## Два режима эксплуатации

| Режим | Кто крутит органы | Когда |
|-------|-------------------|--------|
| **Operator** | человек / Cursor-агент вручную | отладка, разметка, новый урок |
| **Embodied relay** | `sensory_relay` daemon | непрерывная жизнь + уроки в inbox |

Оба режима сходятся в **один** `events.jsonl` + тот же ingest.

---

## Отношение к MCP

| Вопрос | Ответ |
|--------|--------|
| MCP внутри `field_state`? | **Нет** |
| MCP как периферия? | **Да** — через `PeripheryCaptureBackend` |
| Обязаны ли все использовать MCP? | **Нет** — только адаптер обязателен |
| Cursor operator | вызывает MCP напрямую **или** те же backends что prod |

Регистрация backend: конфиг `casa/sensory/backends.json` (или env): `capture=mcp_webcam_capture`, `hearing=whisper_v1`.

---

## Фазы внедрения

| Фаза | Deliverable | Критерий готовности |
|------|-------------|---------------------|
| **P0** | Документ + ручной live (ADR-0026 команды) | sample `events.sample.jsonl` → ingest → слова на L3 |
| **P1** | Adapter + Transport queue + perception plugins | CI stub path |
| **P1b** | CCU `percept_to_mm_event` + FieldBus publish | compositor отделён от Whisper |
| **P1c** | `sensory_loop` + `McpCaptureBackend` live | один сеанс без Cursor chat |
| **P1d** | `FileReplayBackend` | регресс без железа |
| **P2** | inbox `kind: mm_events` + loop с `agent_inbox_runner` | уроки + live в одном процессе |
| **P3** | `mm_action` + TTS + ASR feedback | echo-сценарий «повтори слово» |
| **P4** | детекторы → `vision.objects[]` → `prism_visual` | не только OCR-текст |

---

## Non-goals (v1)

- Нет end-to-end «VLM внутри von-neumann store».
- Нет хранения сырого видео в `ltm/`.
- Нет требования, чтобы `agent_life_tick` сам вызывал MCP (пока relay снаружи; см. open Q1).
- Нет универсального CV палочек в v1 (ADR-0026).

---

## Open questions (обсуждение)

### Q0 — Слои (в обсуждении, не закрыто)

**Твоё предложение:** Периферия ↔ **Адаптер** ↔ Перцепция ↔ Мозг.  
**Моё дополнение (спорное, обсудить):** по аналогии с CIDE между адаптером и мозгом ещё **Transport**, **CCU**, **FieldBus**; 4 слоя — сжатая карта, не полный список.  
**CDS (Q7):** куда вешать compositor «поверхности» для оператора — см. § CDS ниже; в мозг Неймана не тащить.

### Q6 — FieldBus с v1 или позже?

| Вариант | Плюс | Минус |
|---------|------|--------|
| **Сразу in-process FieldBus** | как CIDE 0099; ingest подписчик | чуть больше кода |
| **Прямой вызов ingest** | проще P0 | сложнее добавить второго подписчика |

**Предложение:** P1 — прямой вызов; P1b — ввести `FieldBus.publish(MmEventReady)` перед рефактором orchestrator.

### Q1 — Оркестратор: отдельный процесс или inbox-runner?

| Вариант | Плюс | Минус |
|---------|------|--------|
| **A. Отдельный `sensory_relay`** | чистые зоны ADR-0025; проще CI | два процесса |
| **B. Ветка в `agent_inbox_runner`** | один daemon | смешение teacher + sensory |
| **C. Поток в `agent_life` (будущее)** | «настоящее тело» | риск oracle/блокировок IO |

**Предложение черновика:** A + B (общая библиотека `casa/sensory/loop.py`, два CLI).

### Q1b — Где живет код адаптера/перцепции?

| Вариант | Смысл |
|---------|--------|
| **`casa/sensory/`** в ontology-payload | рядом с ingest; один репо |
| Отдельный пакет `casa-sensory` | если переиспользование вне CASA |

**Предложение:** `casa/sensory/` в payload; адаптер не импортирует `prisms.memory` кроме вызова `ingest_mm_events` из оркестратора.

### Q2 — Динамика `analyze_av_sequence` в канон?

- **Минимум:** только теги в `canon.context` (`av:motion_high`, `av:scene_cut@t`).
- **Средне:** отдельное поле `mm_event.dynamics` (не в predict v1).
- **Максимум:** отдельные эпизоды на `lattice_thal_relay` — нужна спека призмы.

### Q3 — Кто «учитель» для live?

- Human в комнате (approve/reject в UI)?
- Скрипт с `teacher_feedback` в `mm_action`?
- Пока только offline corpus + редкий operator?

### Q4 — Именование organ MCP в репо

Единый префикс `casa-organ-*` vs текущие `webcam-capture-mcp` / `webcam-analysis-mcp` — косметика или контракт версий?

### Q5 — Частота окон внимания

`window_ms` 1200 vs длительность burst 10s — одно событие на burst или нарезка по scene cuts из analyze?

---

## Согласование с ADR-0026

| ADR-0026 | ADR-0027 |
|----------|----------|
| `mm_event` schema | не меняется |
| `ingest_mm_events` | вызывается relay |
| Live «через MCP в Cursor» | частный случай **operator mode** |
| Ограничения v1 OCR/ASR | остаются; органы могут усложняться без смены канона |

После принятия 0027: в 0026 добавить одну строку в § Live: «prod path = sensory relay (ADR-0027)».

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-02 | Черновик для обсуждения (органы MCP, relay, фазы, open questions) |
| 2026-06-02 | Четыре слоя: периферия → адаптер → перцепция → мозг; MCP = backend |
| 2026-06-02 | CIDE-aligned: DAL, Transport, Perception, CCU, FieldBus; таблица parity с 0012 |
