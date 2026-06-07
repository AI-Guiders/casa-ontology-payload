# CASA-ADR-0047: Hippo surprise — привязка concept_id vs emergent extract

**Статус:** accepted; v0 **done** (#1–4, #6); #5 planned  
**Дата:** 2026-06-06  
**Область:** `append_episode`, `run_sleep`, `predict_mismatch`, load governor, F0 emergent  
**Связано:**

- [CASA-ADR-0034-executor-learning-loop.md](CASA-ADR-0034-executor-learning-loop.md) — PDCA Check → hippo; Act → sleep
- [CASA-ADR-0036-emergent-morph-agreement.md](CASA-ADR-0036-emergent-morph-agreement.md) — emergent на поле после sleep, не oracle на write
- [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) — мосты emergent, не teacher expect
- [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md) — cognitive overload → defer verbalize
- `casa/domain/load_governor.py` — overload retire (v0)
- `casa/prisms/tick/pdca_check_tick.py` — `surprise_to_hippo_episode`
- `casa/prisms/memory/agent_curiosity.py` — what-if probes

---

## Решение (одной фразой)

**Два контура памяти, не один:** per-episode sleep merge требует **`concept_id` (bindable episode)**; emergent F0 в хвосте sleep **минтит новые концепты из кластеров**, но **не back-fill'ит** orphan hippo и **не снимает** их с `hippo_pending`. Эпизоды без класса и без resolve → deadlock overload; нужны **типы эпизодов + resolve на write/sleep**, а не надежда что F0 «сам догадается».

---

## Контекст (incident von-neumann, 2026-06-06)

| Наблюдение | Значение |
|------------|----------|
| `hippo_pending` | 15 surface episodes, `concept_id: null` |
| `run_sleep` | `merged: 0`, очередь не убывала |
| `load_governor` | `overloaded: true` → `subject_disposition: defer` |
| Диалог | «разгружу внимание», хотя sleep **вызывался** |

**Причина не «не спал»**, а **«спал, но не мог слить»**: per-episode loop в `run_sleep` без `concept_id` не вызывает `_strengthen_concept` → эпизод вечно в `pending`.

---

## Вопрос: emergent не выводит concept_id?

**Частично — да, но другим контуром и не для всех эпизодов.**

```text
  append_episode (hippo)
        │
        ├─► Lane A: per-episode merge (run_sleep for-loop)
        │      needs concept_id → strengthen on lattice
        │      без id → pending++  ◄── deadlock здесь
        │
        └─► Lane B: F0 emergent batch (run_sleep tail, queue drained path)
               gate_pattern_rows_by_predict_fail
               extract_emergent_count_patterns / names / mul_equiv / successors
               vis↔math / vis↔lex bridges
               → mint NEW concept_id on field (math.pattern.emerged.*, edges)
               → does NOT set ep.concept_id
               → does NOT mark orphan ep consolidated
```

| Механизм | Что emergent выводит | Привязка к hippo ep |
|----------|----------------------|---------------------|
| F0 pattern/names/equiv (sleep tail) | `math.pattern.emerged.*`, `math.num.*`, graph edges | Нет — работает по **кластеру** `episodes[]`, mint отдельно |
| `goal_emergent.propose_goal_from_surprise` | `goal.revise.*`, route | Цель в WM, не поле ep |
| Kolb relink / revise (Act adjust) | edge relink vis↔lex | После surprise + frame context, не generic orphan |
| `concept_id_for_surface(bundle, correct)` | id из **одной** surface | Только если `correct` = буква/слог/слово |
| `_hypothesis_concept_id` (Kolb CE) | id если hyp уже `grapheme.*` / `math.*` | Только Kolb concrete, не macro tick |

**Вывод:** emergent **не обязан** и **сегодня не умеет** вывести `concept_id` для:

- macro tick `predict_mismatch`, где `correct = "grapheme.cyrl.а, grapheme.cyrl.б, …"` (диагностика, не surface);
- what-if / curiosity (`correct=""`, cue `3*2`, scene `what_if`);
- math surface без claim в bundle (`1/2`, `=`).

F0 может **параллельно** вырастить структуру на поле, но **orphan ep остаётся в hippo** → load governor считает backlog → overload.

---

## Почему так сложилось (design intent)

| Intent | Код | Проблема |
|--------|-----|----------|
| Kolb / what-if без oracle | `correct=""`, open cue | Episodic **signal**, не commit |
| Surprise = наблюдение mismatch | `correct=join(surprise)` | Удобно для journal, бесполезно для `concept_id_for_surface` |
| Emergent только после честного опыта | F0 gates, min clusters | Не заменяет **binding** literacy surprise |
| Sleep merge = strengthen shelf | `_strengthen_concept(cid)` | Требует **уже известный** cid |

Канон ADR-0036: учитель не подставляет lemma — но **surprise concepts из control уже известны агенту**; класть их в `correct` вместо `concept_id` — **encoding bug**, не emergent philosophy.

---

## Решение: классы эпизодов + resolve

### 1. Классы (enum `episode_bind_class`)

| Класс | Пример | `concept_id` на write | Учёт в `hippo_pending` / load |
|-------|--------|------------------------|----------------------------------|
| **bindable_surprise** | macro tick predict mismatch | **обязателен** (`surprise[0]` или `primary_surprise_concept`) | да |
| **bindable_correction** | teacher correction, ingest | resolve из surface/bundle или explicit | да |
| **open_probe** | what-if, Kolb CE без expect | опционален | **нет** или TTL (не гонит overload) |
| **rule** | rule_id | rule shelf | да |

### 2. Resolve на write (Check phase)

`pdca_check_tick.surprise_to_hippo_episode`:

```python
concept_id = _primary_surprise_concept(control)  # уже есть в goal_emergent
append_episode(..., concept_id=concept_id, correct=observed, structure_tag="predict_mismatch")
```

- `correct` остаётся human-readable mismatch;
- `concept_id` — канон для sleep merge и deliberate practice.

### 3. Resolve на sleep (pre-merge pass)

Перед strengthen loop — **`resolve_episode_concept_id(ep, bundle)`**:

1. `ep.concept_id` если есть;
2. parse `correct` / `surface_attempt` на `grapheme.*|lang.*|math.*` (regex как в kolb_relink);
3. `concept_id_for_surface(bundle, ep.cue, lattice_id)` для grapheme/word;
4. если `structure_tag=predict_mismatch` и всё ещё null → **`episode_bind_class=open_probe`** или journal-only retire (не strengthen).

### 4. Open probe lifecycle

- Не increment `hippo_pending` в `assess_cognitive_load` **или** cap + TTL ticks;
- F0 tail **может** питаться кластерами open_probe;
- После emergent mint — optional **`link_episode_to_mint(ep_id, minted_cid)`** (phase 2).

### 5. Overload safety valve (v0 **done**)

`load_governor.retire_stuck_surprise_episodes` + `should_force_sleep_on_overload`:

- при `overloaded` и ep без `concept_id` после `min_recurrence` → `consolidated` + `overload_retired`;
- **не** substitute для bind/resolve; предотвращает вечный defer диалога.

---

## Что emergent остаётся делать (без изменений канона)

- F0 batch extract **после** per-episode pass — mint структур math/vis **из опыта**, без teacher oracle;
- `goal_emergent` → arbiter → Kolb revise — **цель**, не hippo binding;
- Deliberate practice / weakest_link — на **bound** concept после fix (1).

Emergent **не отменяет** bindable_surprise: literacy mismatch уже несёт concept ids в `control.surprise` — это не «угадай lemma», это **уже декодированное поле**.

---

## Non-goals

- LLM-in-sleep для infer concept_id;
- Авто-merge ep с `correct=""` без F0 cluster или Kolb RO;
- Подмена subject defer при overload — defer остаётся; overload должен **реально** разгружаться через sleep+resolve.

---

## Порядок реализации

| # | Задача | Acceptance | Статус |
|---|--------|------------|--------|
| 1 | Overload → force sleep + retire stuck | von-neumann pending→0, load↓ | **done** v0 |
| 2 | `surprise_to_hippo_episode`: `concept_id=surprise[0]` | sleep merge ≥1 на literacy surprise lab | **done** |
| 3 | `episode_bind_class` на append | open_probe не считается в load | **done** |
| 4 | `resolve_episode_concept_id` pre-merge | parse correct / surface → cid | **done** |
| 5 | `link_episode_to_mint` после F0 | cluster mint clears source eps | planned |
| 6 | Lab: 15 orphan reproduce → bind → sleep drains | CI smoke | **done** smoke |

**Smoke:** `python -m casa.domain.episode_bind_smoke`

---

## Связь с диалогом (ADR-0045)

Verbalize «разгружу внимание» при `cognitive_overload` **корректен**, если sleep реально снижает load. Пока orphan hippo не bindable — нужен safety valve (#1) и bind (#2–4). Иначе субъект **честно обещает** разгрузку, которую infra не выполняет.

---

## Резюме для партнёра

| Вопрос | Ответ |
|--------|-------|
| Почему нет concept_id? | Episodic signal записали без bind; `correct` — текст, не id |
| Emergent не выводит? | F0 выводит **новое на поле**, не привязывает ep; goal/Kolb — другой контур |
| Что делаем? | Bind surprise на write; классы ep; resolve на sleep; open_probe вне load |
| Что уже есть? | Overload sleep + retire stuck (v0) |
