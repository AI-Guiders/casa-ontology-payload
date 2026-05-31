# Teacher correction protocol v0 — что поправляет взрослый (и что не делает)

**Date:** 2026-05-31  
**Status:** accepted (lab norm; закрывает пробел sleep-cue)  
**Parent:** [`language-acquisition-loop.md`](language-acquisition-loop.md), [`understanding-contract.md`](understanding-contract.md), [`context-axis.md`](context-axis.md), [`infancy-corpus-phases.md`](infancy-corpus-phases.md)  
**Companion:** [`casa-wake-sleep-concept.md`](casa-wake-sleep-concept.md), [`bukvar-text-modality.md`](bukvar-text-modality.md)  
**Lab norm + preflight:** [`kb-casa-teacher-sleep-lab-norm-v1.md`](kb-casa-teacher-sleep-lab-norm-v1.md) — agent-notes primary; cards: `lab/kb/teacher_correction_cards.v1.json`  
**Не CASA:** human L1 evidence — agent-notes `worlds/cognition-language-acquisition/` (`kb-language-acquisition-scientific-evidence-v1.md` + per-paper cards; `transfer_boundary: deny` → spec)

---

## Пробел, который вскрыл sleep lab

Ранний cue `кор` + babble `кoro` → учитель **насильно** дал **`корова`** и sleep укрепил одну лемму.

Это **анти-паттерн**:

| Что видим | Почему плохо |
|-----------|--------------|
| Префикс **`кор`** | В lexicon десятки продолжений: **кор**, кора, корм, **короб**, **коробка**, **коровий**, король, … |
| Babble **`кoro`** (mixed script) | Ошибка **мета-уровня** (алфавит), не выбор между корова/короб |
| Teacher → **корова** | Oracle одного существительного **без сцены**; игнор **коровий** (прилаг.) и **короб*** |
| Sleep strengthen `lang.word.корова` | Записали в «биографию» ложный выбор учителя |

**KB не пустой** — north star уже описывает listen → babble → **мягкая** correct ([`language-acquisition-loop.md`](language-acquisition-loop.md)). Пробел был в **lab cue**, который схлопнул разные оси ошибки в «корова для gate green».

---

## Contур critic → teacher (CASA)

```text
  LISTEN mass (фаза 2)   — ingest без teacher quiz на токен
       │
  B0→B2 (букварь)       — grapheme → syllable → word на поле
       │
  SURFACE               — черновик с поля; ошибки ожидаемы
       │
  CRITIC                — какой тип ошибки?
       │
       ├── meta (раскладка, script mix)     → rule, не lemma
       ├── phonotactic (звук/слог)           → B0/B1 repair
       ├── incomplete prefix                 → wait / preview fork, не oracle
       ├── lexical (какое слово?)            → scene / lexical_ask
       ├── morph (форма, не лемма)           → morph_surface в фразе
       └── ortho (написание выбранного слова) → surface episode на committed target
       │
  SLEEP                 — только подтверждённое critic + teacher + correction_kind
```

На prefix **`кор`** T9 держит **fork** — это не «ещё не выбрал слово» в педагогическом смысле, а **контракт preview**: teacher **не** collapse в одну лемму без scene/commitment.

---

## Типы поправки учителя (Extract → sleep)

| `correction_kind` | Когда | Пример | Extract | Sleep merge |
|-------------------|-------|--------|---------|-------------|
| **`script_rule`** | mixed latn/cyrl, wrong layout | `кoro` → «один алфавит» | `append_rule_episode` | `R:script.*` |
| **`wait_prefix`** | префикс короткий, fork жив | `кор` → **не** collapse | hippo **hint** only (roadmap) | **нет** lemma strengthen |
| **`lexical_ask`** | несколько лемм на prefix | «Ты про **короб** или про **корову**?» | episodic + **scene** | только после ответа |
| **`morph_surface`** | лемма ок, форма нет | «не корова, а **коровий**» | surface + POS edge (roadmap) | целевая **форма** |
| **`ortho_surface`** | слово выбрано, написание нет | «коровa» → «корова» | `append_episode` | `lang.word.*` |

**Порядок:** всегда **сверху вниз**. Mixed script **до** lexical. Lexical **после** commitment или явного disambiguation.

---

## Префикс `кор` — что должен показывать preview (Use до учителя)

T9 на **`кор`** — **конкуренция**, не ответ:

- кор, кора, корм, корд, … (короткие, частые)
- короб, коробка, король, корова, **коровий**, … (длиннее; частота + длина в score)

**Коровий** — не «ошибочная корова», а **другая часть речи** и другой intent. Учитель не «приземляет на корову», а либо **ждёт** окончания слова, либо спрашивает **в контексте фразы** («коровий what?»).

Sleep **не** должен из одного mixed-script surface на `кор` записать «значит корова» — confound entity-hub (cow↔корова) с **episodic teacher**.

---

## Сцена обязательна для lexical correct

Минимальный контракт (roadmap в `understand_extract()`):

```json
{
  "scene": "описали коробку на столе",
  "prefix": "короб",
  "babble": "коробк",
  "teacher": "коробка",
  "correction_kind": "ortho_surface"
}
```

```json
{
  "scene": "молоко, про коров",
  "prefix": "коров",
  "babble": "коров",
  "teacher": "коровий",
  "correction_kind": "morph_surface"
}
```

Без `scene` / `correction_kind` bench **не** должен вызывать `append_episode` с произвольным `correct`.

---

## Lab sleep UC (исправленный v1)

| Cue | Назначение |
|-----|------------|
| **`sleep_mixed_script_kor_v1`** | `teacher_rule_only`: mixed `кoro` на prefix `кор` → только `R:script.no_mixed_alphabet`; **без** strengthen lemma |
| **`sleep_ortho_in_scene_v1`** | полное слово в сцене, ortho fix | ✅ `sleep_tick_cues.v1.json` |
| **`sleep_morph_koroviy_v1`** | фраза с прилагательным, не noun oracle | ✅ |
| **`sleep_lexical_ask_kor_v1`** | lexical ask → pending hippo, no strengthen | ✅ |

**Use после rule-only sleep:**

- prefix `кор` — **fork** ≥ N anchors (кор, кора, корм, …); **нет** искусственного скачка одной леммы
- rule `script.no_mixed_alphabet` — votes↑ на L3

---

## Связь с entity hub

`entity.cow` ↔ `корова` — **cold L3**, для bilingual preview (`co` → cow|со…). Это **не** license учителю выбирать «корова» на каждый кириллический `кор`.

---

## Anti-patterns (явно)

- Oracle lemma на коротком prefix ради green bench
- Sleep strengthen без `correction_kind`
- Путать **homoglyph `co`** с **Russian `кор`**
- POS/taxonomy batch ingest подменяет **episodic lexical ask**

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-31 | v0: протокол типов correct; anti-pattern korova; rule-only sleep lab |
| 2026-05-31 | v0.1: убран import педагогики; CASA contour вместо «как дети» |
| 2026-05-31 | v0.2: preflight + surface_error + cues ortho/morph/lexical_ask; code in `preflight_teacher`, `surface_error` |
