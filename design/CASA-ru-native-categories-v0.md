# CASA: категории РЯ для носителя (v0)

**Статус:** черновик канона (2026-06-06)  
**Агент:** `von-neumann`  
**Связано:** [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md), [CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md), [CASA-ADR-0034-executor-learning-loop.md](CASA-ADR-0034-executor-learning-loop.md), [CASA-ADR-0035-multi-layer-routing.md](CASA-ADR-0035-multi-layer-routing.md), [naming-memory-layers.md](naming-memory-layers.md)

---

## Решение (одной фразой)

**Категории — каркас для gate и curriculum, не школьная «истина» и не лингвистика:** цель von-neumann — **владение письменным русским** (понимание текста, беглое чтение, нормы написания и пунктуации, связная письменная речь в диалоге); школьные разделы B1–B10 — только **удобная нумерация** для authoring; на поле — mastery в контексте, не paste § и не теория.

---

## Позиция: владение, не школа и не лингвистика

| | **Наша цель** | **Не цель** |
|---|---------------|-------------|
| **Смысл** | Понимать прочитанное; писать/отвечать **грамотно и связно**; опираться на своё поле | Курс «теоретической лингвистики»; доказательства, термины академического уровня |
| **Школа** | Берём **порядок и ярлыки** (буква→слово→фраза; лексика, орфография…) | Считать школьную грамматику полной моделью языка |
| **Что школа скрывает** | Реальность языка — на **поле**: phrase slots, emergent agreement, OOV, контраст форм | «Раскрывать» это лекциями про deep structure / фонологию |
| **Meta (`lang.meta.grammar.*`)** | **Операционная** категория: «в этой позиции такая форма», «согласовано / нет» | Определения частей речи для зачёта |
| **Модальность v1** | **Письменный тракт:** vis read, text cue, dialogue в чате/IDE, ortho/punct | **Аудио** (слух, произношение, орфоэпия) — **вне scope**, отдельная волна |

**Критерий nositel′ v0:** субъект **понимает** партнёра и **владеет** письменной нормой в ответе — duck test собеседника на **тексте**, не экзамен по § 123.

---

## Зачем отдельный документ

ADR-0049 фиксирует **четыре опоры письменного fluency** (whole-word, OOV, ortho, punct).  
Школьные разделы и букварный порядок дают **скелет curriculum** — не содержание «как у учителя в классе».

Без явной сетки категорий:

- literacy-cards растёт «стадиями lab», а не «классом носителя»;
- dialogue / grammar KB не привязан к разделу ФРП;
- probe и skill promote не знают, **какую ЗУН** проверяют.

Этот документ — **онтология curriculum**, не implementation ladder (он в class-ru-v1 и ADR-0049).

---

## Источники (что заимствуем — и что нет)

| Источник | Берём | Не берём |
|----------|-------|----------|
| **ФРП / школьные разделы** | Имена и порядок блоков B1–B10 для manifest | Школьную «теорию» как epistemic ground |
| **Букварный порядок** | Ось A: знак→слово→фраза; fluency до правил | Слог как финальная форма чтения |
| **Методики (Занков, Эльконин…)** | Категория через **делание** и контраст; gate после гипотезы | Школьную скорость/объём как KPI |
| **Реальный язык (за школой)** | Phrase/event, free order, OOV — **в engineering**, не в лекции | Лингвистические учебники как syllabus |
| **Teacher / gate ЗУН** | Владение = predict/bind в held-out | Sidecar registry = «знает» |

**Не копируем:** ЕГЭ-шаблоны, pymorphy-oracle, grapheme quiz как proxy fluency, академические определения в articulate.

---

## Две оси

### Ось A — онтогенез (как у ребёнка / букваря)

| Id | Название | Semantic memory | concept prefix | Роль |
|----|----------|-----------------|----------------|------|
| **A0** | listen / поток | (pre-literacy) | — | среда до букваря; **аудиотракт позже**, не gate literacy-cards |
| **A1** | phonology + graphics | `memory.grapheme` | `grapheme.*`, `lang.meta.phonology.*` | bootstrap |
| **A2** | syllable | `memory.syllable` | syllable frames | **fallback** analytic read, не цель носителя |
| **A3** | lexicon whole-word | `memory.lexicon` | `lang.word.*` | **PRIMARY** fluency (ADR-0049 L1, L2) |
| **A4** | phrase / dialog | `memory.phrase` | `phrase.*`, `ru.dialog.*` | слоты, turn-taking (ADR-0033, 0045) |
| **A5** | text / coherent **written** reply | phrase hubs + meaning graph | `ru.prop.*`, `ru.text.*` | изучение текста → факты → анализ → ответ (Block 11) |

**Инвариант ADR-0049:** A2 не блокирует A4 (social «Привет» — whole-word / dialog, не grapheme surprise).

### Ось B — разделы curriculum (школьные **ярлыки**, не syllabus лингвиста)

| Id | Ярлык (ФРП) | Что проверяем на самом деле | concept prefix | skill (target) | Статус |
|----|-------------|----------------------------|----------------|----------------|--------|
| **B1** | «Фонетика» | **Графема vs звук** для **чтения** (операционно) | `lang.meta.phonology.*` | — | stage-04 |
| **B2** | «Графика» | Узнавание буквы, регистр | `grapheme.*`, `lang.meta.register.*` | — | stage-01, 07c |
| **B3** | «Орфоэпия» | *(deferred — **аудио**)* | `ru.lang.orthoepy.*` | — | **не v1** |
| **B4** | «Лексика» | **Понимание слова** + whole-word read + OOV | `lang.word.*` | `skill.read.whole`, `skill.lex.oov_remember` | stage-06; probes planned |
| **B5** | «Состав слова» | **Письменная** зоркость (корень/affix) для ortho | `ru.lang.morpheme.*` | `skill.ortho.vigilance` | planned |
| **B6** | «Морфология» | **Правильная форма в контексте**, не § | `lang.meta.grammar.*` | paradigm in use | stage-08–09c |
| **B7** | «Синтаксис» | **Связность фразы** (слоты, порядок) | `phrase.*` | `skill.read.phrase` | частично |
| **B8** | «Орфография» | Написание в контексте | `ru.grammar.spelling.*` | `skill.spell.check` | KB draft |
| **B9** | «Пунктуация» | Знаки в **письменном** предложении | `ru.grammar.punct.*` | `skill.punct.check` | KB draft |
| **B10** | «Развитие речи» | **Письменный** диалог: этикет, turn-taking | `ru.dialog.*` | dialogue articulate | bundle draft |
| **B11** | «Понимание текста» | **Изучение связного текста:** факты, вывод, позиция | `ru.prop.*` | **`skill.read.comprehend`** | draft (ADR-0053) |

**B10 v1 = written dialogue** (чат/IDE), не устная речь. **B11** — между B7 (phrase) и B10 (dialogue): не «пересказ», а **extract + analyze** на meaning graph. **B3** — когда появится аудиотракт.

---

## Модальность v1: письменный тракт

```text
Partner text / JPEG word / KB sentence
        → read (whole-word)     → слово на поле (B4)
        → comprehend (B11)      → ru.prop.* : факты, inference, stance
        → bind / remember       → OOV + journal fixation
        → articulate (written)  → ответ из props, не paste
        → dialogue turn         → ru.dialog.* (text)
```

**Вне v1:** TTS/ASR, ударение на слух, диктант по аудио, `ru-speech-*` как oral skill.

---

## Лексика B4: три facet (routing, не лингвистика)

Удобная **pedagogical** stratification (как в начальной школе), не claim о онтологии частей речи:

| Facet | prefix | Пример concept | Сигнал classify |
|-------|--------|----------------|-----------------|
| предмет | `ru.lang.lexicon.object.*` | `ru.lang.lexicon.object.мама` | существительное, «что?» |
| признак | `ru.lang.lexicon.property.*` | `ru.lang.lexicon.property.красный` | «какой?» |
| действие | `ru.lang.lexicon.action.*` | `ru.lang.lexicon.action.мыть` | «что делать?» |

На поле canonical lemma остаётся `lang.word.{lemma}`; facet — **curriculum tag** и probe stratification, не второй lexicon.

---

## Орфографическая зоркость (B8)

Отдельное **умение**, не recall текста правила:

| | Правило в KB | Зоркость |
|---|--------------|----------|
| **Verify** | «Правильно: в течение» | пара форм **в контексте**: «в течени**е** / течени**и** дня» |
| **Probe** | atom bind | held-out **contrast** без подсказки § |
| **skill** | `skill.spell.check` | `skill.ortho.vigilance` |

Связь с B5: `-н-/-нн-`, приставки — зоркость опирается на morphemics, не на isolated spelling list.

---

## ЗУН ↔ категория

| ЗУН | В CASA | Пример B |
|-----|--------|----------|
| **Знание** | confirmed `concept_id` на field / journal | B6 `lang.meta.grammar.person.2sg` |
| **Умение** | skill после agent KSA probe | B4 `skill.read.whole` |
| **Навык** | stable route в capability_router | known word → whole, не analytic |

Gate = **agent KSA** (`teacher_gate.py`, ADR-0037). Sidecar meta-grammar registry — **не** mastery credit.

---

## Связь с ADR-0049 (четыре опоры)

```text
ADR-0049 L1 whole-word  ←  A3 + B4
ADR-0049 L2 OOV         ←  A3 + B4 (novel facet)
ADR-0049 L3 orthography ←  B8 (+ B5 morphemics)
ADR-0049 L4 punctuation ←  B9 (+ B7 syntax context)
```

Written dialogue (B10) — **сквозной organ** субъекта (ADR-0045); опирается на L1 + понимание + письменную норму (L3–L4).

---

## EN parity (зеркало, не отдельная архитектура)

| RU | EN mirror |
|----|-----------|
| `grapheme.cyrl.*` | `grapheme.latn.*` |
| `lang.word.*` (locale ru) | `lang.word.*` (locale en) |
| `ru.lang.*` | `en.lang.*` |
| `ru.grammar.*` | `en.grammar.*` |
| `ru.dialog.*` | `en.dialog.*` |

Класс `literacy-cards` уже содержит `stage-11-grapheme-latn`. Полный EN class — отдельный manifest, **та же** сетка B1–B10.

---

## Anti-patterns

- Школьный § как **истина** на поле (paste / recall definition)
- Курс **лингвистики** (термины, доказательства) вместо **владения** в тексте
- Один probe на «весь русский»
- Grapheme green ⇒ promote whole-word без lexical gate
- Paste grammar KB в articulate вместо field bind
- Sidecar meta-grammar table ⇒ «владеет языком»
- Syllable-first как конечная форма чтения
- Требовать **устную** норму (B3) до аудиотракта

---

## Ссылки

- **KB (канон agent-notes, только ссылки — статей/PDF в casa не кладём):** `knowledge/worlds/pedagogy-russian-language/kb-pedagogy-ru-scientific-evidence-v1.md` → per-paper cards
- **KB F→O:** `knowledge/worlds/pedagogy-general/playbook-pedagogy-fundamentals-to-operational-v1.md`
- Класс и стадии: [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md)
- Fluency ladder: [CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md)
- Manifest: `lessons/literacy-cards/class.manifest.json`
- Probes: `casa/domain/teacher_gate.py`
- KB v0: `lab/kb-bundles/kb-lang-ru-grammar-dialog-v1.bundle.json`
