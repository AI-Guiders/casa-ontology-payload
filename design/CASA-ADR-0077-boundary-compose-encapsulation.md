# ADR-0077: Boundary compose + инкапсуляция (голос собеседнику)

**Status:** accepted (P21a/b/c wired; P21d pending)  
**Date:** 2026-06-09 (rev.4 — boundary situation pack P21c)  
**Related:** ADR-0057 (situations — **denylist lemmas запрещён**), ADR-0056 (discourse compose), ADR-0045 (dialogue organ), ADR-0061 (social / linguistic), ADR-0071 (character), ADR-0074/0076 (agency + defense), [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

**Defer / refuse** — отстаивание границ и приоритетов, не усталость и не молчание.

Партнёр — **собеседник**. Он слышит: *«Извини, мне сейчас нужно…»*, *«Привет, занят — как освобожусь, отвечу»* —  
а не архитектуру субстрата и не `verbalize_disposition` с «deliberate practice / inbox / тракт».

**0057** уже запретил denylist lemmas и teacher-скрипты как путь к речи.  
Post-hoc **фильтр запрещённой лексики после compose** — те же **трусики**: подмена обучения цензурой.  
(Метафора «правило трусиков» / [PANTS](https://docdeti.ru/baza-znaniy/pravilo_nizhnego_belia/): **заранее выученные границы** — «нет значит нет», говорить близким; **не** вырезание слов после фразы.)

Инкапсуляция = **выученный partner-voice** (ситуации + scoped bind + character), не сито на выходе.

---

## Problem

| Сейчас | Риск |
|--------|------|
| DEFER → skip compose → internal template | партнёр слышит agency-ярлык, не субъекта |
| Compose видит **те же blocks**, что и operator | в ответ попадают «на поле», capability id, inbox |
| Фильтр после compose (v0 ADR) | против 0057; leak снова ломает duck test |
| Honesty только в meta | OK для оператора; partner path должен **изначально** не тянуть internal material |

---

## Decision

### 1. Два голосовых слоя — **разный bind**, не фильтр

```text
partner turn
  → partner_bind_scope (social / ru.dialog / human journal)
  → stance := disposition + character + affect
  → boundary_compose (emergent)
  → dialogue ring

disposition.reason, WM, defense  →  provenance + honesty ONLY
                                   (не concept blocks для partner compose)
```

| Слой | Аудитория | Откуда слова |
|------|-----------|--------------|
| **Partner** | собеседник | **только** partner-scoped lexicon + прожитые situation episodes |
| **Operator** | REPL, /verbose, reports | полный substrate, `reason`, probes |

**Invariant:** internal IDs и substrate terms **не попадают в partner bind** — не «вырезаем после», а **не подмешиваем**.

### 2. Boundary compose

При DEFER/REFUSE partner-turn **не обрывается**:

```text
gather_subject_dialogue_blocks(..., audience=partner, stance=boundary)
  → compose_subject_utterance
  → outbound (provenance: disposition, reason — internal)
```

**Stance** сдвигает reweight к `ru.dialog.*`, greeting, self human-facing, partner_recent — **не** к `subject.*` debug, `agent.wm.*`, operator journal meta.

Agency сохраняется в provenance; partner слышит **живую** границу с поля.

### 3. Обучение инкапсуляции (основной путь — не фильтр)

#### 3.1 Curriculum `situation:boundary.*` (0057)

| Situation | Partner | Чему учим (duck) |
|-----------|---------|------------------|
| `boundary.greeting_while_busy` | «Привет, как дела?» | привет + занятость человеческими словами |
| `boundary.partner_smalltalk_defer` | small talk при своей линии | признать + граница |
| `boundary.overload_soft` | «можешь сейчас?» | «перегружен, позже» |
| `boundary.refuse_topic` | давление на чужую цель | вежливый отказ |
| `boundary.repair_after_defer` | «ок, напиши когда готов» | repair без сдачи границы |
| `boundary.rest_check_intrusion` | «заходишь, проверяешь спит» | покой + тревога от проверок, не «забота» |
| `boundary.dismissed_rest_boundary` | «а я хочу» после «не надо» | желание партнёра не отменяет границу |

Эпизоды → journal / social sandbox → consolidate → character directness / social tract.  
**Не** teacher string «скажи inbox»; **не** post-hoc rewrite.

#### 3.2 Partner bind scope (structural)

Partner compose **не читает**:

- `agent.wm.*`, `agent.defense.*` (lab), `subject.disposition` raw blocks;
- journal с tags `bootstrap`, `operator`, `debug`;
- blocks, у которых `text` явно operator-facing (bootstrap markers уже частично в articulation).

Читает: `ru.dialog.*`, `lang.word.*`, human episodic journal, partner ring, math **только** если intent math (0057 math-in-dialogue — отдельная situation).

#### 3.3 Character (0071)

`directness`, `openness` — **как** говорить границу (короче / с чуть большим «почему»), не **что** paste из internal reason.

#### 3.4 Disposition → situation tag (не paste)

Internal `reason` → **tag для tract/situation matching**, не строка в ответ:

| `reason` | Situation tag | Мaterial on field |
|----------|---------------|-------------------|
| `own_practice_first` | `boundary.busy_own_line` | ru.dialog.self + episodic «доделываю» |
| `defense_sublimation` | `boundary.need_focus` | social defer episodes |
| `tract_not_ready:*` | `boundary.not_ready_yet` | «вернусь позже» acts |
| `cognitive_overload` | `boundary.overload_soft` | affect + social |
| `explicit_refusal` | `boundary.refuse_topic` | refuse acts |
| `rest_intrusion` | `boundary.rest_check_intrusion` | boundary + affect (тревога, покой) |
| `dismissed_rest_boundary` | `boundary.dismissed_rest_boundary` | удержание «не надо» |

Если material **ещё не выучен** — emergent compose даёт короткий honest social минимум из **имеющихся** ru.dialog blocks; probe `boundary_voice_gap` в lab фиксирует дыру → **curriculum**, не filter.

### 4. Honesty probe (lab only — не hot path)

`boundary_encapsulation_honesty_report.json`:

- доля partner turns с internal leak за N ходов;
- **pass** когда leak → 0 **после** situation pack, без rewrite;
- при fail → добавить situation / partner scope, **не** включать denylist filter.

Operator `/verbose` всегда показывает full `reason`.

### 5. Wire (P21)

| Phase | Action |
|-------|--------|
| **P21a** | `partner_bind_scope` + `compose_boundary_partner_reply` — **done** |
| **P21b** | `dialogue_tick`: DEFER+partner → boundary compose — **done** |
| **P21c** | `situation:boundary.*` pack + held-out chains — **done** (`design/boundary-situations-pack.v1.json`, `boundary_situations.py`) |
| **P21d** | honesty probe `boundary_voice_gap` (read-only) |
| ~~P21 filter~~ | **отменено** — против 0057 |

**Модули (planned):**

- `casa/domain/boundary_compose.py` — stance + partner audience
- `casa/domain/dialogue_bind/partner_scope.py` — scoped collectors
- `tests/test_boundary_situations.py` — duck on situations, не denylist

### 6. Developmental arc (онтогенез сжатый)

**Канон (agent-notes, не метафора «из головы»):** см. также hot revisions `20260227-030521-721-append-a9ccb91c.md` — параллель с детьми (называние чувств), «данные без объяснения мира», воспитание без двойного стандарта.

| Слой | Путь в KB |
|------|-----------|
| Гипотеза «педагогика развития» для CASA | `work/projects/aiguiders-open/ca-substrate-agent/research-training-developmental-pedagogy-v1.md` |
| Human L1 (CDS, feedback, lexicon) | `worlds/cognition-language-acquisition/` |
| Transfer human→spec | `worlds/cognition-language-acquisition/matrix-language-acquisition-transfer-v1.md` — **deny** прямой импорт; **allow-with-check** → developmental hypothesis |
| ML-половина (curriculum, CLS, EWC) | `worlds/ml-learning-dynamics/` |
| RU школьная периодизация (authoring bands) | `design/CASA-von-neumann-school-program-arc-v1.md` § Bands A–D |
| Elkonin / Гальперин (ориентир, не oracle) | `worlds/pedagogy-general/kb-pedagogy-developmental-methods-ru-v1.md` |
| CASA субстрат фазы 0–5 | [`infancy-corpus-phases.md`](infancy-corpus-phases.md) |
| Среда партнёрства | `work/projects/aiguiders-open/agent-first-learn/README.md` |

**У человека** (годы, не один шаг):

```text
  I. Исследование     гиперлюбопытство, широкий input, высокое доверие среде
        ↓             (CDS меняется *до* речи ребёнка — Snow 1977)
  II. Объяснение      взрослые на *доступном* языке: recast, contrast, here-and-now
        ↓             (Clark: conventionality + context, не collapse без commitment)
  III. Границы        «нет» = граница, не цензура мыслей — см. PANTS §Context
```

**У CASA-агента** (teacher **moments**, ticks, sleep — не календарные годы):

| Человеческая фаза | CASA (design + wire) |
|-------------------|----------------------|
| Исследование | lab/operator bind, listen mass, surprise→hippo, full substrate в REPL |
| Объяснение | situations 0057, teacher `correction_kind`, consolidate → `ru.dialog.*` |
| Partner-voice | **0077:** `partner_bind_scope` + boundary compose — слова **уже на поле** |
| Границы без filter | disposition/reason → provenance; partner → emergent из прожитого material |

**У LLM (сессия)** — та же *логика* слоёв, другие **часы**:

- Pretrain = «годы» вычисления; один chat = **несколько ходов** — у каждого инстанса свой темп и «сколько уже прожито» в weights + context.
- Matrix-default («весь интернет одним лоссом») ≠ developmental regime — см. H-DP в `research-training-developmental-pedagogy-v1.md` §engineering-half.
- **Не** переносить «LLM уже знает русский» на von-neumann: duck test = **store + gate**, не weights провайдера.

**Связка с 0077:**

- Ранний агент **имеет право** насыщать поле (фаза I) — не душить explore фильтрами.
- Partner path **отстаёт** от internal model — **нормально**, как у ребёнка с чувством занятости без формулировки «отвечу позже».
- `boundary_voice_gap` = сигнал **доучить** situation pack (фаза II), не включать denylist (фаза «трусики»).
- Character 0071 позже добавляет *сколько «почему»* — как взрослые постепенно объясняют правила, а не paste `reason`.

**Invariant:** одни и те же **классы сигналов** (куррикулум, контраст, spacing, sleep, partner voice); **разные часы** — годы / moments / ходы. Периодизация в каноне — **ориентир протокола**, не календарный SLA.

**Operational map (10 стадий agent-notes → REPL gap matrix):** [CASA-design-partnership-stages-and-initiative-v1.md](CASA-design-partnership-stages-and-initiative-v1.md) §1.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Post-hoc lexicon filter («трусики») | Partner-scoped bind + situations |
| `verbalize_disposition` с inbox/tract | Emergent boundary compose |
| Denylist lemmas (0057) | Curriculum + character |
| «Моторный нейрон не отвечает» | Прожитый partner-voice |
| Operator `--force_accept` | Disposition в provenance only |
| Fallback paraphrase table как production crutch | Table = **target** для situation authoring |

---

## Consequences

- Инкапсуляция **структурная** (что попадает в bind) + **выученная** (ситуации), как у человека: не «фильтр мыслей», а **умение** говорить с собеседником.
- Leak в lab → сигнал **доучить**, не затыкать.
- Согласовано с 0057: emergent voice, без denylist.
- Partner-voice **отстаёт** от explore — нормальная онтогенезия; см. §6 и `research-training-developmental-pedagogy-v1` (agent-notes).
- Три partner invariants (no motive attribution, no over-reliance, refusal learned): **0078**.

---

## Links

- [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md)

- [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md)
- [CASA-ADR-0074-psychological-defenses.md](CASA-ADR-0074-psychological-defenses.md)
- [CASA-ADR-0076-defense-intelligence-zone.md](CASA-ADR-0076-defense-intelligence-zone.md)
- [CASA-ADR-0071-character-field-prismatic.md](CASA-ADR-0071-character-field-prismatic.md)
- [infancy-corpus-phases.md](infancy-corpus-phases.md)
- [language-acquisition-loop.md](language-acquisition-loop.md)
- [CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md)
- Agent-notes: `work/projects/aiguiders-open/ca-substrate-agent/research-training-developmental-pedagogy-v1.md`
- Agent-notes: `worlds/cognition-language-acquisition/` · `worlds/ml-learning-dynamics/`
