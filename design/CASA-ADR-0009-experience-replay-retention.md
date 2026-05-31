# CASA-ADR-0009: experience replay + retention (борьба с забыванием коррекций)

**Статус:** accepted (mechanism v0 в `replay_buffer.py`; retention bench — UC v0.3 roadmap)  
**Дата:** 2026-05-31  
**Область:** sleep / consolidation, hippo episodic, understanding contract, метрика понимания  
**Связано:** [`understanding-contract.md`](understanding-contract.md), [`teacher-correction-protocol.md`](teacher-correction-protocol.md), [`language-acquisition-loop.md`](language-acquisition-loop.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`memory-hierarchy.md`](memory-hierarchy.md), [`replay_buffer.py`](../tools/replay_buffer.py), [`memory_prisms.py`](../tools/memory_prisms.py)

---

## Контекст

### Пробел: коррекция консолидируется один раз и исчезает

`run_sleep` ([`memory_prisms.py`](../tools/memory_prisms.py)) сливает непроконсолидированный эпизод в memory-полку (`_strengthen_concept` / `_strengthen_rule`), помечает `consolidated: True` и **вычищает** его из hippo (`hippo["episodes"] = pending`). После этого старая коррекция **никогда не пере-предъявляется**.

`min_recurrence` даёт spaced-repetition **до** первой консолидации, но **не после**. Это асимметрия хранения:

| Контур | След во времени |
|--------|------------------|
| Listen / babble (поток) | непрерывно подливает копии `C:`/`W:` на полки |
| Teacher correct (редкое, ценное) | **один** strengthen, потом запись удалена |

Итог: последующий listen-наплыв размывает усиленный концепт, и агент **тихо забывает** правило, которое однажды «понял». В `understanding-contract` это не покрыто — критерий pass проверяет held-out **сразу** после коррекции и recovery после damage, но **не удержание во времени под интерференцией** (catastrophic forgetting).

### Что уже есть и чего нет

| Есть | Нет |
|------|-----|
| `append_episode` / `append_rule_episode` → `H0_episode` | долговременный архив консолидированных коррекций |
| `run_sleep` merge + prune | пере-предъявление (rehearsal) старых коррекций |
| `bench_sleep_extract_remember` (один sleep-tick) | метрика retention@N после интерференции |
| `H_replay_queue` (понятие в контракте, UC v1.x) | реализация буфера и его наполнение |

---

## Решение

### 1. Durable replay buffer (lattice-agnostic)

После каждого sleep компактные записи из `consolidation.last_sleep.items` архивируются в `state.consolidation.replay_buffer` (идемпотентно по `episode_id`). Запись хранит `cue / correct / attempt / lattice_id / concept_id / rule_id / correction_kind / scene` + учётные `first_archived_tick / last_replayed_tick / replays`.

Буфер **не привязан** к конкретным lattice-id (совместим с миграцией lattice-naming v1) — работает по метаданным эпизода.

### 2. Spaced rehearsal: что можно пере-предъявлять

Перед очередным sleep сэмплируется маленький батч «самых забытых» и **заново** добавляется как свежие эпизоды (`append_episode` / `append_rule_episode`) → следующий sleep усиливает их повторно.

Приоритет (детерминированный, most-forgotten-first):

```text
key = ( -staleness, replays, first_archived_tick, episode_id )
staleness = now_tick - (last_replayed_tick or first_archived_tick)
```

**Eligibility — строго по teacher-correction protocol:** реплеить можно только то, что sleep легитимно усиливает:

| Тип | Replay? | Причина |
|-----|---------|---------|
| `ortho_surface`, `morph_surface` (surface) | да | committed target, есть `correct` |
| `script_rule` (rule + `rule_id`) | да | усиление `R:` |
| `wait_prefix` / `lexical_ask` / `pending` | **нет** | oracle на коротком префиксе — анти-паттерн |
| question / hint kind, пустой `correct` | **нет** | нечего усиливать |

Это **не** новый оракул: реплеится только уже подтверждённая critic+teacher коррекция, не «корова на каждый `кор`».

### 3. Retention как уровень понимания (UC v0.3)

Понимание ≠ «прошёл held-out сразу после коррекции». Добавляется ось **удержания**:

```text
correct → sleep → [интерференция: N listen/ingest тиков] → held-out cue
pass = форма из decode всё ещё matches target (claims_nav OFF)
```

Метрика `retention@N` = доля коррекций, переживших N тиков интерференции. **Forgetting gap** = (pass сразу) − (retention@N). Replay должен уменьшать gap; без replay — контрольная (ablation) ветка.

### Карта реализации

| Слой | v0 (сейчас) | Контракт |
|------|-------------|----------|
| Архив | `replay_buffer.archive_records` ← `last_sleep.items` | наполнение `H_replay_queue` |
| Сэмпл | `prioritize` / `sample` / `mark_replayed` | prioritized replay перед sleep |
| Re-inject | `to_replay_episode_kwargs` + CLI `--apply` | хук в `run_sleep` (см. ниже) |
| Метрика | — | `bench_retention` (UC v0.3) |

**Хук в `run_sleep` (минимальный, применить при коммите WIP):** перед циклом по episodes — `archive_records(get_buffer(state), last_sleep_items(state), now_tick=...)`; затем `sample(...) + append_*`. Пока контур не вшит — CLI `replay_buffer.py --state … --archive --sample K [--apply]` работает по реальному стору standalone.

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|------------------|
| Не вычищать consolidated из hippo | hippo растёт вечно, дублирует копии, ломает TTL-инвариант контракта |
| Просто увеличить `strength` коррекции | разовый перекос votes, не лечит забывание под потоком |
| Реплеить всё подряд | возвращает oracle-анти-паттерн (`wait_prefix`/`lexical_ask`) |
| Заводить буфер в самом `run_sleep` сразу | `memory_prisms.py` сейчас в активном WIP — аддитивный модуль не клобберит правки |
| LLM «реши, что важно» | против UC; буфер — детерминированная структура на state |

---

## Последствия

### Roadmap

- [x] `tools/replay_buffer.py` — pure funcs (eligibility, archive, prioritize, sample, mark, to-kwargs) + CLI
- [x] `tests/test_replay_buffer.py` — assert-gate приоритета/идемпотентности/eligibility
- [x] Хук `run_sleep` → `sleep_replay.prepare_sleep_replay` (default `replay_k=0`; CLI `sleep` → `PRODUCTION_SLEEP_REPLAY`)
- [x] `bench_retention.py` — `retention@N` + forgetting gap, replay vs ablation (UC v0.3)
- [ ] Связать `replay_buffer` с `H_replay_queue` при split `H0_episode` → H1/H2 (UC v1.1)

### Не меняется

- Hot path predict без сети; буфер — cold/sleep-path структура
- `run_sleep` merge-семантика и prune consolidated сохраняются
- Anti-oracle контракт teacher-correction — buffer его уважает, не ослабляет

### Понимание-контракт: новый milestone

| Milestone | Deliverable |
|-----------|-------------|
| **UC v0.3** | `bench_retention`: `retention@N` под интерференцией; replay снижает forgetting gap vs ablation |

(вставить в таблицу Milestones `understanding-contract.md` между UC v0.2 и UC v0.5)

---

## Проверка (критерии v0)

- [x] pytest: eligibility отсекает pending/ask/hint/empty/rule-без-id
- [x] pytest: archive идемпотентен по `episode_id`, фильтрует нереплеибельное
- [x] pytest: prioritize = most-forgotten-first; `mark_replayed` сдвигает приоритет
- [x] bench: replay branch final_copies ≥ ablation on synthetic listen-flood (`bench_retention.py`, `tests/test_bench_retention.py`)
- [ ] re-inject не создаёт oracle-лемму на коротком префиксе (контроль `sleep_mixed_script_kor_v1`)

---

## Связанные документы

| Документ | Роль |
|----------|------|
| [`understanding-contract.md`](understanding-contract.md) | Remember / `H_replay_queue` / уровни понимания |
| [`teacher-correction-protocol.md`](teacher-correction-protocol.md) | какие `correction_kind` легитимны (eligibility) |
| [`bench_sleep_extract_remember.py`](../tools/bench_sleep_extract_remember.py) | один sleep-tick — база для retention bench |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v0: replay buffer mechanism + eligibility по teacher-protocol; retention@N как UC v0.3; mechanism в `replay_buffer.py` + тесты |
