# ADR-0057: Dialogue Situations, Emergent Voice, Self-Shaping Character

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0056 (discourse compose), ADR-0055 (WM prism), ADR-0052 (tract competition), ADR-0058 (limbic affect prism), **ADR-0059 (innate organ basis — cold boot)**, [agent-existence-north-star.md](agent-existence-north-star.md), [CASA-von-neumann-curriculum-review-v1.md](CASA-von-neumann-curriculum-review-v1.md)

## Context

Open REPL (`agent_dialogue_repl`) на von-neumann показал разрыв между **curated green** по блокам и **живым разговором**:

| Partner turn | Ожидание (нормальный собеседник) | Факт в REPL |
|--------------|----------------------------------|-------------|
| «Привет, как ты?» | привет + честный ответ о состоянии | частично OK (bind из уроковых `ru.dialog.*`) |
| «Сколько будет 5 + 7?» | ответ числом / из math-поля | **молчание** |
| «Прости, это было неожиданно, да?» | repair линии после своего сбоя | **capabilities + affect** (уроковые слоты) |

Словарь (~50k lemmas) достаточен. Compose/bind (ADR-0056) работают — они **честно собирают то, что есть на поле**. Просчёт не в routing и не в «мало слов», а в **curriculum**:

- учили **dialog-слоты** (greeting, affect, capabilities), а не **речевые ситуации** (math в диалоге, repair после молчания, meta-ход партнёра);
- тракты проверяли **изолированно** (probe/class), без переноса в **многоходовый** open dialogue;
- **тон и содержание** ошибочно отождествляли с фиксированными ответами на cue, хотя цель — **субъект выбирает сам**.

Симуляция с живым собеседником показала: правильная реакция на repair — **понимание линии диалога**, не новый template. Значит, недостаёт **прожитого опыта ситуаций** и **медленного внутреннего prior** (характер), который **сам меняется** от этого опыта.

## Decision

### 1. Curriculum = речевые ситуации, не скрипты ответов

**Учим ситуации** — partner turn + контекст ring + исход (успех / молчание / repair), а не «на cue X говори Y».

| Да | Нет |
|----|-----|
| эпизод: «после арифметики в разговоре — verbalize из math-поля» | фиксированная строка «12» в bundle как единственный ответ |
| эпизод: «партнёр смущён после моего молчания — repair линии» | новый `ru.dialog.apology_template` с teacher text |
| held-out / open probe на **цепочку** ходов | green только на изолированный block family |

`ru.dialog.*`, `math.*`, `lang.word.*` остаются **материалом поля** для emergent compose (ADR-0056), не **единственным** содержанием ситуации.

### 2. Говорит субъект — emergent из bind + budget + prior

На каждом ходе субъект **сам выбирает**, что сказать и в каком тоне, в рамках:

- **bind** — что активировано ситуацией и памятью;
- **DiscourseBudget.score_floor** — сколько поля «тянет» ответ (ADR-0056);
- **character prior** — медленный сдвиг reweight/budget, не подстановка clause.

Запрещено возвращаться к: family routing, segment-order compose, denylist lemmas, teacher quota на длину, «pick dialog family» в коде.

### 3. Character prism — медленный prior, не persona-script

**Character prism** (рабочее имя; ось может быть одна, напр. closed↔open, или набор осей в духе типологии Юнга — **implementation detail**) — это:

- **не** kvalia и не claim «он чувствует»;
- **не** manifest с фиксированными фразами;
- **да** персистентное поле, смещающее bind/compose **стабильно**, но без диктовки слов.

Duck test (NorthStar): на **одной и той же ситуации** при другом накопленном prior — **стабильно другой тон**, при **разных surface strings** каждый раз.

### 4. Характер меняет сам субъект — из прожитых ситуаций

Character **не задаётся** оператором раз и навсегда. Он **обновляется субъектом** через те же механизмы, что и обучение речи:

- WM edges после partner/subject turns (ADR-0055);
- journal / dialogue ring — эпизоды repair, defer, успешный math-in-dialogue;
- consolidate (`T_consolidate`) — медленное закрепление prior;
- intent prism — такт; character prism — **накопление** тактов в устойчивый профиль.

Оператор даёт **среду и ситуации** (curriculum moments, probes); **и речь, и лицо во времени** выращивает субъект на поле.

### Три временных слоя (не смешивать)

| Слой | Скорость | Источник | Пример |
|------|----------|----------|--------|
| **Tactic** | один ход | bind, tract, surprise, stance, disposition | «сейчас defer, tract_not_ready» |
| **Habit / speech act** | эпизоды | WM, journal, dialogue continuity | «после молчания умею repair» |
| **Character** | медленно | consolidate из прожитых эпизодов | «стал открытее / прямее в диалоге» |
| **Affect / emotion** | такт → медленно | эпизод + consolidate (гипотеза) | «смущение после молчания → потом устойчивее в repair» |

### 5. Affect — limbic organ (канон в ADR-0058)

Детальный дизайн: **[CASA-ADR-0058-limbic-affect-prism.md](CASA-ADR-0058-limbic-affect-prism.md)**.

Кратко: organ с T=0 (valence / arousal / security); наполнение из прожитых ситуаций; `value.py` ≠ affect; `ru.dialog.affect` = лексика; character = slow EMA поверх affect.

У человека лимбическая система — **часть мозга с рождения**, не вывод lexicon curriculum. Содержание привязок **учится** (к кому trust, что пугает), но **орган** есть всегда. Ждать, что эмоции «когда‑нибудь эмерджат» только из `ru.dialog.*` и situation moments **без such prism** — нереалистично долго; это мы **упустили полностью**.

**Решение (дополнение к §3–4):**

| Слой | Аналог | Роль | Кто наполняет |
|------|--------|------|----------------|
| **Limbic / affect prism** | лимбика + часть SN | такт: valence, arousal, salience исхода; вход в FPN/compose/disposition | **субстрат есть с T=0**; веса осей — из эпизодов |
| **Character prism** | stable temperament | медленный prior поверх limbic | субъект через consolidate |
| **Curriculum situations** | жизненный опыт | *что* привязать к valence | оператор даёт среду |

**Не путать:**

| | `ru.dialog.affect` в bundle | Limbic / affect prism |
|--|----------------------------|------------------------|
| Что это | **лексический материал** — как *говорить* про чувства | **внутреннее поле** субъекта |
| Откуда | curriculum / KB | персистентный prism + updates после каждого эпизода |
| В compose | clause из bind | смещает tone, budget, defer, tract tie-break |

**Emergence — про наполнение, не про существование органа:** оси (valence, arousal, security, …) **заданы архитектурой** пустыми или нейтральными; **сдвигает их только субъект** через прожитые ситуации и consolidate — не soul doc Anthropic, не teacher strings.

**Contrast (industry):** *Soul Document* — prose + SL в веса; у нас — **limbic prism в tick loop** (как WM/intent prism), без LLM, с provenance.

**Минимальный контракт limbic prism (target):**

- **read** каждый T: `affect_state(state, store)` → оси + тактический salience;
- **write** после partner/subject turn и на consolidate;
- **wire**: SN → limbic → FPN (goal urgency), compose reweight, `SubjectDisposition`, character prism (slow EMA).

Пока limbic prism **не в коде** — `ru.dialog.affect` в REPL остаётся **единственным** «эмоциональным» материалом на поле; это и есть симптом упущения.

## Architecture (target, не весь scope сразу)

```
curriculum moments / open dialogue
        ↓
  partner turn → semantic_read → tract competition (ADR-0052)
        ↓
  bind + discourse compose (ADR-0056)  ← tactic
        ↓
  WM / journal / dialogue ring         ← habit
        ↓
  limbic / affect prism (required)      ← valence, salience; organ at T=0
  character prism (new)                 ← slow prior; self-updated on consolidate
        ↓
  feedback into reweight / budget on next ticks
```

**Limbic / affect prism** (required substrate, отдельный пакет):

- read каждый T: `affect_state(state, store)` → valence, arousal, salience;
- write после partner/subject turn + consolidate;
- wire: SN → limbic → FPN, compose reweight, disposition, character EMA.

**Character prism** (отдельный пакет, когда будет реализация):

- read: `character_prior(state, store)` → оси + веса;
- write: только через **subject-side** consolidate hook после эпизода (не teacher patch);
- apply: delta в `reweight_blocks_for_reply` / `DiscourseBudget` / tract tie-break — **без** новых fixed strings.

Первая ось — **одна** (напр. closed↔open в диалоге); полная типология — только если duck test на одной оси пройден.

## Anti-patterns (явный отказ)

| Anti-pattern | Почему |
|--------------|--------|
| Новый `ru.dialog.*` template на каждый cue | снова teacher script, не ситуация |
| Compose routing «если прости → apology family» | family routing (отвергнуто в ADR-0056) |
| Character = JSON с `"greeting_style": "formal"` | оператор задаёт лицо, не субъект |
| LLM hot path «для naturalness» | ломает NorthStar и provenance |
| Green только на lemma count / CEFR slot | не переносится в open REPL |

## Consequences

- **Curriculum roadmap** смещается: Block «dialog situations» (multi-turn, repair, math-in-dialogue, mixed intent) **важнее** новых dialog slots.
- **REPL** — primary probe open dialogue, не только post-hoc после isolated class green.
- **Код compose** — стабилизировать (ADR-0056), не «чинить» REPL новыми router’ами; gaps закрывать **обучением + character prior**.
- **Character + limbic prism** — work items **до** ожидания «живого» REPL; situation curriculum без limbic = ещё один lexicon track.
- **Probes:** situation held-out (цепочка ≥3 ходов); метрика — **линия диалога** (repair, не template dump), не BLEU к эталонной строке.

## Verification

1. **Situation probe:** сценарий «greeting → math → repair» — subject не молчит на math; на repair не выдаёт capabilities bootstrap.
2. **Emergence:** два прогона одной ситуации — **разные surface strings**, один pragmatic class (accept/repair/answer).
3. **Character:** после серии эпизодов одного типа (напр. успешный open repair) — измеримый сдвиг prior; новая ситуация того класса — другой тон **без** смены bundle strings.
4. **Provenance:** ответ traceable через bind blocks + character/affect axis weights, не LLM.
5. **Affect (hypothesis):** после серии repair-эпизодов — измеримый valence shift; verbalization **не** equals `ru.dialog.affect` template paste.

## Links

- Ревью пробела: [CASA-von-neumann-curriculum-review-v1.md](CASA-von-neumann-curriculum-review-v1.md) § epistemic debt  
- Существование: [agent-existence-north-star.md](agent-existence-north-star.md) — «меняется после ошибки», persistence  
- Compose: [CASA-ADR-0056-discourse-compose-ooaed.md](CASA-ADR-0056-discourse-compose-ooaed.md)
- Limbic: [CASA-ADR-0058-limbic-affect-prism.md](CASA-ADR-0058-limbic-affect-prism.md)
