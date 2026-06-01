# CASA-ADR-0023: Sleep at scale — thin-first, batched consolidate, no GPU merge

**Статус:** принято (design); код v1 = `run_sleep(max_episodes=)` + `sss_sleep --batch-size` (R1–R2); monolithic по умолчанию  
**Дата:** 2026-06-01  
**Область:** `run_sleep`, hippo queue, runtime checkpoint, lab ingest  
**Связано:** [`memory-hierarchy.md`](memory-hierarchy.md), [`CASA-ADR-0017-compact-persist.md`](CASA-ADR-0017-compact-persist.md) (thin checkpoint, `ltm/`), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md) (NCA на GPU), [`CASA-ADR-0025-autonomous-execution-tier.md`](CASA-ADR-0025-autonomous-execution-tier.md) (T1 Engine, persist hot path), [`casa-wake-sleep-concept.md`](casa-wake-sleep-concept.md), [`CASA-ADR-0022-agent-v1-existence-bar.md`](CASA-ADR-0022-agent-v1-existence-bar.md) (B2 hippo + consolidate), [`prism-memory-architecture-v1.md`](prism-memory-architecture-v1.md) § P2

---

## Контекст

Lab store `ingest-ref-afan` после mass listen: **~335k** эпизодов в `prism_hippo`, fat `field_state.json` (~250+ MiB с `cells[]`), один вызов `run_sleep` + `--compact-persist`.

Наблюдения (2026-06-01):

| Симптом | Причина |
|---------|---------|
| Wall time десятки минут, **низкий общий CPU** (~один поток Python) | Один цикл `for ep in episodes` + GIL; не matmul |
| CPU time процесса << wall time | **I/O-bound**: `json.load`/`json.dump` fat checkpoint, flush 133× `.ltm` |
| GPU не задействован | Merge = dict + `Grid._place_token`; NCA regrow — опциональный **хвост** sleep |

**Ошибочная гипотеза:** «перенести sleep на GPU». NCA/CUDA уже отведены под **damage→regrow одной решётки** (train/repair), не под консолидацию episodic queue.

---

## Решение (одной фразой)

**Порядок:** сначала **thin checkpoint + shipped `ltm/`**, потом **батчевый** `run_sleep` с checkpoint между батчами; **не** плодить hippo на ingest, если факт уже на L2; **GPU только** для NCA (ADR-0002), не для merge loop. Архитектурная метафора — **вытесняющая многозадачность** (§ ниже), не «один ночной скрипт на весь корпус».

---

## Neuro analogy & вытесняющая многозадачность (non-claim)

**Дисклеймер:** это **инженерная аналогия** для scheduling и бюджетов памяти, не модель нейробиологии и не claim «как настоящий мозг». См. ADR-0022 § граница с AGI.

### Что перенимаем от «мозг не умирает от параллели»

Биология держит устойчивость через **много контуров** + **лимиты** + **прерывание**, а не через один поток на всё сразу:

| Идея (folk → design) | CASA |
|----------------------|------|
| Поток сознания / внимание | tick, **P0 hot**, `sn.active_prism`, predict на **одной** content-призме |
| Быстрая запись «что только что было» | **P2 hippo** — малая очередь, не копия `ltm/` |
| Медленная кристаллизация | **sleep** → strengthen → `ltm/` |
| Не держать всё в ОЗУ | thin checkpoint, router без полной гидратации всех призм |
| Сон кусками, не один dump | **batched sleep** (этот ADR) |

### Вытесняющая многозадачность (preemptive multitasking)

Полезная модель из ОС: у процесса есть **квант** и **приоритет**; планировщик **вытесняет** долгую работу, если пришло более срочное (ввод, surprise, лимит ресурса). Цель CASA — не «больше потоков Python», а **явный scheduler поверх подсистем**, чтобы долгий sleep **не блокировал жизнь агента**.

```text
                    ┌─────────────────────────────────────┐
   HIGH priority     │  TICK (wake): input, predict,      │
   preempts         │  surprise → hippo, hot prune        │
                    └─────────────────┬───────────────────┘
                                      │ вытесняет
                    ┌─────────────────▼───────────────────┐
   LOW (фон)        │  SLEEP JOB: batch consolidate,     │
   yield/checkpoint│  compact_persist, NCA regrow       │
                    └─────────────────────────────────────┘
```

| Механизм ОС | CASA (v0 / v1) |
|-------------|----------------|
| **Process** | призма + роль: `content`, `hippo`, `hot_context`, `router`, `control`, **`prism_control_thalamus`** (relay/arousal, ADR-0024) |
| **Context switch** | `resolve_route` → `sn.active_prism`; смена lattice hint |
| **Time slice** | один **batch** sleep (`max_episodes`); между батчами — `save_runtime_state` |
| **Preemption** | **v0 lab:** monolithic sleep = «критическая секция» (плохо). **v1:** tick может стартовать между батчами; **v2:** явный `SleepJob` с флагом `cancel_requested` / `sn.mode=wake` прерывает фон |
| **Priority boost** | `control.value` / surprise → hippo append **раньше** фоновой consolidate |
| **Backpressure** | `HIPPO_EPISODE_SOFT_CAP`, hot hard prune — очередь не растёт бесконечно |
| **Swap / page file** | shipped **`ltm/`**; runtime checkpoint — только episodic/meta |
| **Cooperative yield** | батч завершился → kernel maintain → persist → **уступить** CPU/I/O следующему tick |

**Инвариант вытеснения:** пока агент **живой** (autonomous tick), **ни один** lab/offline job не должен держать store эксклюзивно часами без checkpoint и без возможности resume. Monolithic sleep на 335k — антипаттерн; batched sleep — шаг к cooperative; tick между батчами — шаг к preemptive.

### Что **не** смешивать

| Метафора | Не значит |
|----------|-----------|
| «Как мозг» | биологическая точность, сознание, квалиа |
| «Многопоточность» | обязательно `threading`/`multiprocessing` на каждый эпизод |
| «GPU = параллельный мозг» | CUDA только под NCA repair (ADR-0002), не под merge |
| Preemptive sleep | вытеснение **долгого job**, не прерывание `_strengthen_concept` на полпути внутри одного эпизода (v1: гранулярность = **эпизод**, не токен grid) |

### Связь с multi-prism (ADR-0016)

«Много процессов асинхронно» в продукте — это **не** 335k потоков, а **мало долгоживущих контуров** (memory, math, vis, control) + **короткоживущие** записи в hippo/hot. Router решает, **какой** content-контур в фокусе; sleep **не** сливает призмы — только укрепляет решётки выбранной и снимает обработанные эпизоды (transfer matrix, ADR-0021).

### Roadmap scheduler (design)

| ID | Поведение |
|----|-----------|
| S1 | `SleepJob` state: `batch_index`, `pending_count`, `interrupted_at` |
| S2 | Между батчами: если `sn.mode == wake` и есть input queue — **отложить** следующий batch |
| S3 | `prism_memory_health`: `hippo_cap` как сигнал «запланировать sleep job», не блокировать tick |
| S4 | v2: shard workers + coordinator (§5) — отдельные «процессы» на L2_word_XX |

---

## 1. Что делает sleep (и что не ускоряется GPU)

```text
T_sleep (cognitive):
  prepare_sleep_replay (опц.)
  FOR each hippo episode:
    strengthen concept / rule on lattice (CPU, 2D string grid)
    gates (F0 emergent) — branchy Python
  hippo ← pending only
  maintain_memory_kernel (ltm_layout, hot prune, …)
  maybe_compact_persist → ltm/
  save_runtime_state

T_sleep (опц. хвост, GPU):
  nca_regrow_lattice(one lattice, model.pt)  # ADR-0002
```

| Операция | Доминанта | GPU? |
|----------|-----------|------|
| Parse/save fat `field_state.json` | I/O + JSON | нет |
| 335k × `_strengthen_concept` | CPU, мелкие мутации grid | нет (overhead H2D) |
| `compact_persist` N решёток | I/O | нет (v0); параллель записи — v1 ops |
| `nca_regrow_lattice` | CUDA | **да**, если есть `model.pt` |

**Инвариант:** семантика consolidate **не меняется** при батчинге; меняется только **гранулярность checkpoint** и observability.

---

## 2. Thin-first (обязательный порядок на больших store)

См. ADR-0017 § Thin runtime checkpoint.

| Шаг | Действие | Эффект |
|-----|----------|--------|
| S0 | `ltm/` уже заполнен (remigrate L2/L3 + `compact_persist`) | cells на диске |
| S1 | `migrate_thin_checkpoint --write` | `field_state` без `cells[]`, MiB не сотни |
| S2 | Sleep / tick resume | `boot_store` + thin overlay; load быстрый |

**Правило lab:** на store с `len(hippo) > HIPPO_EPISODE_SOFT_CAP` (512) и fat checkpoint — **не** запускать monolithic sleep до S1, если `ltm/pack.manifest.json` актуален.

**Non-goal:** thin не заменяет sleep; только убирает дублирование cells в JSON.

---

## 3. Batched sleep (v1 API)

### 3.1 Поведение

- `run_sleep(state, …, *, max_episodes: int | None = None)` обрабатывает не более **N** неконсолидированных эпизодов за вызов (FIFO или oldest-first — зафиксировать в коде v1).
- После батча: `save_runtime_state(store_dir, state)`; опционально `compact_persist` только если `store.compact_persist_on_sleep` или `--compact-persist` на CLI.
- Повтор until `len(pending_episodes) == 0` или оператор останавливает.

### 3.2 CLI (lab)

`tools/sss_sleep.py` (и tick hook):

| Флаг | Смысл |
|------|--------|
| `--batch-size N` | max episodes per `run_sleep` call (default: all, v0 compat) |
| `--max-batches K` | stop after K batches |
| `--progress` | stderr: `batch i/K, merged, pending, elapsed` (`migrate_progress` стиль) |
| `--thin-first` | if fat checkpoint + manifest: run thin migrate once before first batch |

### 3.3 Orchestrator

`LearningTickConfig`: `sleep_batch_size: int = 0` (0 = legacy all-in-one).

`maybe_sleep_phase`: при `sleep_batch_size > 0` вызывать `run_sleep(..., max_episodes=batch)`.

---

## 4. Ingest: не дублировать опыт в hippo

**Проблема:** mass listen пишет **surface episode на каждый токен**, хотя `concept_id` уже на L2 после ingest → очередь раздувается, sleep O(n) искусственно.

| Режим | Когда | Hippo |
|-------|-------|-------|
| **Curriculum ingest** | lab batch listen, факты уже на решётке | **не** append_episode per token; опц. один summary episode / metrics only |
| **Wake / surprise** | predict mismatch, teacher_correct | append как сейчас (ADR-0015 implicit) |
| **Replay** | sleep `replay_k` | как сейчас |

**Конфиг store (v1):** `store.ingest_episodic_mode: "off" | "surprise_only" | "full"` (default: `full`). В `memory_manifest.json` или runtime `store`; lab listen: `record_listen_surface()` (`casa/prisms/memory/ingest_episodic.py`).

**Инвариант продукт (ADR-0021):** shipped факты в `ltm/`; hippo — **очередь необработанного опыта**, не зеркало корпуса.

---

## 5. Параллелизм (v2, не GPU)

| Подход | Условие | Статус |
|--------|---------|--------|
| Multiprocess по **L2 shard** | эпизод несёт `lattice_id=L2_word_XX`, partition pending | roadmap v2 |
| Параллель `compact_persist` writes | независимые `.ltm` файлы | roadmap ops |
| GPU merge loop | — | **отклонено** |

Кросс-shard эпизоды (virtual `L2_word`) остаются в coordinator-потоке v2.

---

## 6. Observability и health

- Kernel aspect `hippo`: `over_cap` → рекомендация `kernel.run_sleep_consolidate` (уже v0).
- После каждого батча: `consolidation.last_sleep` + `pending` count в stderr при `--progress`.
- Lab: `prism_memory_health` до/после серии батчей; цель `episode_count ≤ cap` или обоснованный `pending` (questions, min_recurrence).

---

## 7. Связь с ADR-0022 (бар v1)

| Критерий | Как этот ADR помогает |
|----------|----------------------|
| B2 забывание / consolidate | batched sleep + меньше мусорных эпизодов |
| A4 самопочинка | thin-first + kernel maintain без «один ручной скрипт на часы» |
| Не AGI | scoped store, не «GPU = AGI» |

---

## 8. Roadmap реализации

| # | Артефакт | Приоритет |
|---|----------|-----------|
| R1 | `run_sleep(..., max_episodes=)` + тест на synthetic hippo | **done** |
| R2 | `sss_sleep.py --batch-size --progress --thin-first` | **done** |
| R3 | `ingest_episodic_mode` + `record_listen_surface` | **done** |
| R4 | `LearningTickConfig.sleep_batch_size` | **done** |
| R5 | `compact_persist` `parallel_writes` / `--parallel-ltm` | **done** (shard sleep v2 — open) |
| R6 | `SleepJob` + yield между батчами | **done** (`sn.input_pending` hook) |
| R7 | § Neuro/preempt — ссылка в `casa-wake-sleep-concept.md` | P2 |

**Lab немедленно (без ожидания R1):** `ingest-ref-afan` — дождаться текущего monolithic sleep; затем thin migrate; следующие прогоны — батчи по 5k–20k.

---

## Non-goals

- Переписать consolidate на CUDA/OpenCL.
- Менять wire format `multi_prism_v1`.
- Автоматически удалять `field_state.legacy.json` без явного ops.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0023: thin-first, batched sleep, ingest hippo policy, GPU boundary |
| 2026-06-01 | § Neuro analogy + вытесняющая многозадачность (non-claim); scheduler roadmap S1–S4 |
| 2026-06-01 | R1–R2: `max_episodes`, batched CLI, `test_run_sleep_batch.py` |
| 2026-06-01 | R3–R6: ingest episodic, tick batch sleep, parallel ltm, SleepJob |
