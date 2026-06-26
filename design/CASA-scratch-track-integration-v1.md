# Scratch: track integration — мы / Дима / cherry-pick / sync lag

**Status:** scratch — для обсуждения оператор + Дима + агенты  
**Date:** 2026-06-16 (fetched `origin` same session)  
**Parent:** [`CASA-scratch-branch-digest-v1.md`](CASA-scratch-branch-digest-v1.md), [`CASA-scratch-listen-wire-gap-v1.md`](CASA-scratch-listen-wire-gap-v1.md), ADR-0081 Track 2, Dima [`ВАЛИДАТОР-СМЫСЛА-статус-и-план.md`](ВАЛИДАТОР-СМЫСЛА-статус-и-план.md) (on `develop`)

---

## Зачем этот док

Две пары **(h+a)** в одном репо. Скорость выше Git Flow. **Лаг синхронизации = продуктовый риск**: без свежего `fetch` агент описывает чужой tip из прошлой сессии (мы уже попали: POC vs 40+ коммитов).

Этот scratch фиксирует **что где лежит**, **что нам нужно**, **что можно забрать**, **что ещё не готово**, и **как часто «смотреть на часы»** в процессе.

---

## Карта веток (после `git fetch origin`)

| Track | Ref @ fetch | Owner | Одна строка |
|-------|-------------|-------|-------------|
| **Наш hot path** | `fix/neumann-free-speech-recovery` → `daa8602` | ты + агент | listen Phase B, life tick, motor speech, impulse (часть локально) |
| **Дима concept net** | `feat/conceptual-network` → `0ff1f22` | Дима + агент | parse → graph → validate → round-trip; situation memory |
| **Integration trunk** | `origin/develop` → `1b4e41c` | merge | **concept net уже влит** (`Merge feat/conceptual-network`) |
| **Общий предок** | `38d1f684` (us ↔ Dima branch) / `25c88f38` (us ↔ develop) | — | разошлись давно |

**Важно:** cherry-pick с `feat/conceptual-network` ≈ cherry-pick с **`develop`** по concept-слою — ветка Димы **уже в develop**. Нам не хватает не «достать у Димы с GitHub», а **`merge develop → our branch`** (или rebase — только по решению людей).

**Нашего в develop пока нет** (8+ коммитов только у нас): life-tick listen wire, motor speech, listen imprint stack, beat toolchain, dialogue L3 composer, …

---

## Что есть у нас (`fix/neumann-free-speech-recovery`)

### Запушено (reviewable)

| Контур | Evidence | Scratch / ADR |
|--------|----------|-----------------|
| Auditory + visual imprint | `listen_moment`, `imprint.py`, cold path | ADR-0028, listen corpus |
| Beat model (operator) | `listen_beat_model`, annotator, Qwen export | не канон просмотра |
| **Life tick + listen stream** | `listen_womb_tick`, `perceptual_prepare_life_*`, orchestrator merge | [`CASA-scratch-listen-wire-gap-v1.md`](CASA-scratch-listen-wire-gap-v1.md) W4–W8 |
| Online A↔V bind | `bridge_vis.bind_av_coactive_on_tick` | W1 online слой |
| Sleep A↔V emergent | `extract_emergent_aud_vis_bridges` | W1 sleep |
| Affect listen | `affect_after_listen_scene` | W5 |
| **Motor speech efferent** | `speech_compose`, `speech_tick`, self-listen, `body/speech_tract` | [`CASA-scratch-motor-speech-wire-gap-v1.md`](CASA-scratch-motor-speech-wire-gap-v1.md) |
| Phase B tools | `listen_womb_tick.py`, `listen_replay_scenes.py` | womb pilot |
| Impulse (cold + частично tick) | `listen_hooks`, ADR-0080 | W6 частично |

### Локально (ещё не push — на момент дока)

| Контур | Файлы | Зачем |
|--------|-------|-------|
| Stream impulse wiring | `sensory_hooks.py`, channels, orchestrator | W6 stream полный |
| Motor agency | `speech_disposition.py`, compose без oracle pool | phonation из поля |
| Scratch canon | branch-digest, listen/motor scratch правки | процесс + Phase B |

### Наш канон (согласовано в диалоге)

- Просмотр = **wall-clock stream**, не beats, не mass re-ingest как цель.
- Пересмотр = **quantity → quality** (sleep, surprise↓, другие детали).
- **Rewatch / familiarity gap** — **ещё не спроектирован** (отдельный slice).

### Чего у нас нет

- Понятийная сеть / text→graph→text.
- `situation_memory` / `situation_store` (узнавание parsed situation).
- Validator equivalence / reality-check harness.
- Bulk bilingual glossary teach.
- Chat `/meaning` deep routing.

---

## Что есть у Димы (уже на `develop`)

Источник правды: tip `0ff1f22`, docs [`ВАЛИДАТОР-СМЫСЛА-статус-и-план.md`](ВАЛИДАТОР-СМЫСЛА-статус-и-план.md), [`ROADMAP-понятийная-сеть-и-язык.md`](ROADMAP-понятийная-сеть-и-язык.md).

### Ядро (готово для lab / demo, тесты зелёные на их CI)

```text
text → parse.py → meaning graph → situation fingerprint
     → validate / equivalence triage (✅ / ⚠️ / ❓)
     → render.py → text   (round-trip)
situation_memory.seen() / recall_similar()
situation_store → persist on field (sit.<id>|edge|…)
concept_net: isa, affords, arg1/arg2 (~4500 concepts)
reality_check: recall 100% on dangerous (не, qty, unit); coverage 2.7% raw KDE, 100% curated
```

### Модули (`casa/curriculum/`)

| Пакет | Назначение | Зрелость |
|-------|------------|----------|
| `concept_net`, `translate`, `glossary` | онтология + RU↔EN names | **stable POC** |
| `situation`, `situation_memory`, `situation_store` | «видел эту конфигурацию?» | **stable POC**, текст |
| `parse`, `roundtrip`, `render`, `grounded` | перевод через смысл | domain-limited |
| `equivalence`, `reality_check` | метрики продукта | **honest numbers** |
| `ask`, `converse`, `triggers`, `software_domain` | вопросы, imperatives, UI domain | modular |
| `analogy`, `attributes`, `quantity`, negation, units | расширения графа | incremental |
| `compose`, `clause`, `sentence`, `bilingual`, … | curriculum capstone | **large**; ADR-0081: не мержить оптом |

### Чего у Димы **нет** (на develop без нашей ветки)

- `listen_womb_tick` → `run_life_tick` на stream.
- `perceptual_prepare_life_sensory` + orchestrator percept merge.
- Motor speech on tick (`maybe_motor_speech_on_tick`).
- Lalabook listen pilot, impulse stream hooks.
- Canon «смотреть мультик как поток».

**Конфликт-пример:** `orchestrator.py` — у нас **+** percept/motor/av_bind; на develop этих блоков **нет** (диалог/curriculum track). Merge = **ручное сохранение нашего life-tick wire**.

---

## Что нам нужно от Димы (приоритет)

| P | Need | Зачем нам | Готово? |
|---|------|-----------|---------|
| **P0** | Осознанный merge **`develop` → our branch** | concept layer без выдумывания | develop готов; **merge не сделан** |
| **P1** | `situation` + `situation_memory` + `situation_store` | прототип «seen before» (пока text; паттерн для rewatch ADR) | **да** на develop |
| **P1** | `concept_net` + `glossary` teach pattern | ADR-0073, motor compose → concept ids | **да** |
| **P2** | `reality_check` + validator docs | честные метрики, не «кажется работает» | **да** |
| **P2** | `grounded` validate-then-render | efferent без hallucination surface | **да**, узкий домен |
| **P3** | Chat `/meaning`, deep routing | не блокирует listen pilot | **да**, опционально |
| **P3** | Full curriculum capstone (`compose`/`clause`/…) | partner school track | **review**; не для listen merge |
| **—** | Video/stream → situation fingerprint | rewatch как у людей | **нет ни у кого** — joint design |

---

## Cherry-pick: можем ли, как, риски

### Рекомендуемый путь (не тысяча cherry-picks)

```text
1. git fetch origin
2. merge origin/develop → fix/neumann-free-speech-recovery
3. Resolve: orchestrator, partner_speech_act, memory_prisms (if any)
4. Keep OUR: percept_life, av_bind, motor_speech, listen_womb, sensory_hooks
5. Tests: listen + motor + test_concept_net* + test_situation*
6. Push integration branch; PR to develop when pilot green
```

**Почему не cherry-pick по файлам:** на develop уже **~40 merge commits** concept net; ручной pick `c1bc9db..0ff1f22` хуже одного merge base.

### Если нужен минимальный инкремент (без full develop)

| Tier | Что взять | Конфликт | Готовность |
|------|-----------|----------|------------|
| **T0 docs** | `ВАЛИДАТОР-СМЫСЛА…`, `ROADMAP-понятийная…`, `ИДЕЯ-понятийной-сети` | нет | ✅ |
| **T1 kernel** | `concept_net.py`, `situation*.py`, `translate.py`, `glossary.py`, `lab/curriculum/concept-net-*.json`, tests | низкий | ✅ |
| **T2 parser** | `parse`, `roundtrip`, `render`, `equivalence`, `reality_check` | средний | ✅ domain-limited |
| **T3 chat** | `casa/cli/chat.py`, demo cmds | средний | ✅ demo |
| **T4 capstone** | whole `compose`/`clause`/bilingual stack | высокий | ⚠️ ADR-0081: review with Dima |
| **✗** | develop's **missing** orchestrator hooks | N/A | **не забирать** — это регресс |

### «Ещё не готово» — честно

| Обещание | Статус |
|----------|--------|
| Universal translator | **нет** — coverage 2.7% on raw KDE |
| Induced ontology from video | **нет** — curated / WordNet |
| Sensory rewatch familiarity | **нет** — ни у нас, ни у Димы |
| LLM-free «понял мультик» | **нет** — listen bind без words[] |
| Stytovka concept net ↔ vis/aud imprint | **design only** (ADR-0073) |

---

## Sync lag: «светло/темно → часы → миллисекунды»

Чем быстрее параллельные (h+a) tracks, тем **мельче единица синхронизации** нужна процессу.

| Эпоха процесса | Достаточно | Ломается когда |
|----------------|------------|----------------|
| Один dev, один branch | «созвон раз в неделю» | — |
| Два human, редкий merge | Git Flow feature week | agent commits daily |
| **Два (h+a) + две tracks** | **fetch каждую сессию** + digest | tip уезжает на 40 commits незаметно |
| Pilot на поле | **+ merge-base age в часах** | двойной imprint, расход canon |
| Continuous agent (будущее) | event log / field_version cursor | calendar useless |

### Ritual (см. [`CASA-scratch-branch-digest-v1.md`](CASA-scratch-branch-digest-v1.md))

**Триггеры:** начало сессии про чужой track · перед merge · «sync» · конфликт canon.

**Минимальный вывод сессии:**

```text
develop @ <hash> <date>
our branch @ <hash> <date>
merge-base age: <N> commits / <days>
themes delta since last session: …
```

**Human sync:** когда merge-base **> ~3–5 дней** или **> ~15 commits** на чужом track — короткий созвон Дима↔ты (агенты digest принесут, люди решают merge order).

Агент **не живёт между сообщениями** — «раз в N дней» не работает; работает **«каждый раз, когда открыли CASA и трогаем интеграцию»**.

---

## Предлагаемый порядок работ (для обсуждения)

1. **Commit + push** наш локальный impulse/agency/sensory_hooks (чтобы develop merge не потерял).
2. **Merge `origin/develop`** в нашу ветку; orchestrator — **keep ours** for listen/motor.
3. **Pilot не менять:** stream → sleep → replay diff (rewatch scratch потом).
4. **Не** тащить T4 capstone в тот же PR, что listen pilot.
5. Совместно с Димой: **rewatch gap** vs `situation_memory` — один design session (text pattern → sensory fingerprint TBD).

---

## Вопросы к Диме (bring to sync)

1. OK merge order: **develop → neumann branch first**, потом наш PR → develop?
2. Orchestrator: concept-net chat routing + **наши** percept/motor hooks — кто ownership?
3. `situation_store` lattice id — совместимо с `agents/von-neumann` store layout?
4. Coverage roadmap: узкий домен A vs hybrid B — что ближе к Von Neumann school path?
5. Ещё commits на `feat/conceptual-network` после `0ff1f22` или только develop?

---

## Связанные gaps (не смешивать в один merge)

| Gap | Track | Doc |
|-----|-------|-----|
| Listen Phase B + motor | ours | listen + motor scratch |
| Concept / validator | Dima / develop | ВАЛИДАТОР-СМЫСЛА, ADR-0073 |
| Rewatch familiarity | **joint, open** | TBD scratch |
| Branch sync | process | branch-digest scratch |
| W9 episode thread | ours | listen scratch W9 |

---

## Anti-patterns

- Описывать Dima tip без `git fetch`.
- Full merge двух tracks «потому что оба green locally».
- Cherry-pick `orchestrator` с develop **поверх** ours без diff review.
- Ждать «когда созреет» — при нашей скорости merge-base = **технический долг в днях**.

---

## Success

Один созвон, одна страница: **«develop = concept net; we = listen+motor; merge X; cherry-pick only Y; rewatch = joint Z; sync = every session + human if >N commits».**
