# CASA-ADR-0049: RU lexical fluency — словарное чтение, OOV, орфография, пунктуация

**Статус:** принято (2026-06-06)  
**Репозиторий:** [casa-ontology-payload](https://github.com/AI-Guiders/casa-ontology-payload)  
**Связано:** [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md), [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md), [CASA-teacher-framework-v1.md](CASA-teacher-framework-v1.md), ADR-0034 (цикл 1–5), ADR-0035 (`skill.read.*`), ADR-0044 (field articulate), ADR-0045 (dialogue), ADR-0048 (KE / KB orient), ADR-0036 (morph-agreement)

---

## Решение (одной фразой)

**Цель von-neumann по русскому — владение письменным языком на поле:** **понимание** текста, **словарное** беглое чтение, **OOV**, **орфография** и **пунктуация** в контексте, **письменный** диалог — через gate ЗУН, field + journal + KB claims; слоговый/analytic read — **bootstrap**; **аудио и лингвистическая теория — не v1**.

---

## Позиция (не школа-as-truth, не лингвистика)

- **Школьные разделы** — ярлыки curriculum ([categories-v0](CASA-ru-native-categories-v0.md)), не epistemic model языка.
- **Gate** — умеет **в тексте** (read, bind, write norm, reply), не «назови термин».
- **Meta-grammar** — operational: форма в контексте, не лекция.
- **Модальность v1:** vis + text; **аудиотракт позже**.

---

## Контекст (gap сегодня)

| Область | Факт на store (2026-06) | Не достаточно для «носителя» |
|---------|-------------------------|------------------------------|
| Чтение | `skill.read.analytic` — fail/surprise на «Привет» (grapheme drill) | Whole-word на знакомых словах |
| Lexicon | T2 `lexicon-ru` ~93 tok; phrase shards из detcorpus | Social + grammar dialogue |
| KB | math + RU-math bridge; `kb-lang-ru-grammar-dialog-v1` (draft) | Полный орфо/пunct corpus + gate |
| Dialogue | journal bootstrap + honest partial без grammar | Explain/check norm из field |
| OOV | KE extract не wired | Новое слово → remember → LTM |

**North star:** субъект **собеседник** (ADR-0045) опирается на **своё владение письменным языком** — понимание и грамотный текст, не LLM-переводчик и не paste KB.

---

## Четыре опоры (target)

```text
                    ┌─────────────────────────────────────┐
                    │  RU native tract (ADR-0049)         │
                    └─────────────────────────────────────┘
         ┌──────────────┬──────────────┬──────────────┬──────────────┐
         │ L1 Lexical   │ L2 OOV       │ L3 Ortho     │ L4 Punct     │
         │ whole-word   │ novel word   │ spelling     │ comma, dash  │
         │ fluent read  │ remember     │ norms        │ norms        │
         └──────────────┴──────────────┴──────────────┴──────────────┘
                              ↓ gate + journal confirmed
                    field LTM · routes · dialogue articulate
```

### 1. Словарное (не слоговое) беглое чтение

| | Bootstrap (есть) | Target (носитель) |
|---|------------------|-------------------|
| **Процедура** | `skill.read.analytic` — буква/слог, R1 | **`skill.read.whole`** — целое слово за один act |
| **Память** | T0 grapheme, T1 syllable | T2 **`lang.word.*`** как lexical unit |
| **Routing** | novel → analytic (ADR-0035) | **known word → whole**; analytic только если OOV или ambiguity |
| **Probe** | `probe_analytic_read_corpus` | **`probe_lexical_read_fluent_ru`** (held-out words, не grapheme list) |
| **Dialogue** | «Привет» → surprise по буквам | «Привет» → `lang.word.привет` / `ru.dialog.greeting` |

**Инвариант:** fluency = **predict_lex / whole-word** на учебном и жизненном cue; analytic — тракт обучения и fallback, не default hot path для знакомых форм.

**Anti-pattern:** бесконечный syllable stage; «зелёный» grapheme quiz ≠ умеет читать слова.

### 2. Запоминание новых слов (OOV, вне корпуса)

Слова, которых **нет** в ingest corpus / detcorpus / KB bundle:

```text
surface (partner / text / periphery read)
  → classify: OOV | known
  → ke.extract / lang.word candidate
  → agent_remember (hypothesis)
  → verify: recall cue, minimal context, no collision
  → journal confirmed → sleep → lang.word.{slug} на LTM
  → (optional K5) promote в KB bundle
```

| concept_id | Смысл |
|------------|--------|
| `lang.word.{lemma}` | лексема на поле |
| `ke.claim.oov.{slug}` | fixation «встретил → значение/роль» |
| `ke.source.{doc}` | provenance |

**Не oracle:** pymorphy / expected surface на wake (Teacher framework).  
**Corpus gap — норма:** агент **учится** OOV так же, как math на поле — не ждать полного словаря в KB.

**Связь ADR-0048:** OOV = подтракт **K1 extract + K4 remember**; orient по KB только для уже ingested claims.

### 3. Орфография

Нормы написания — **atoms**, не paste правил:

| Prefix | Пример |
|--------|--------|
| `ru.grammar.spelling.*` | `v_techenie`, `po-russki`, `takzhe` |
| `ru.grammar.paronym.*` | `nadet_odet` |
| `ru.ortho.*` | (reserved) частые ошибки, `-н-/-нн-`, приставки |

**KB transport:** `kb-lang-ru-grammar-dialog-v1` + расширение `kb-lang-ru-orthography-v1` (planned).  
**Hot path:** bind atom → articulate («Правильно: …» / compare forms); без KB — **honest partial** (уже в `subject_articulation`).

**Gate:** held-out **форма в контексте** («в течение дня», «по-русски»), не таблица правил в wake.

### 4. Пунктуация

| Prefix | Пример |
|--------|--------|
| `ru.grammar.punct.*` | comma before `что`, direct speech, vocative |
| `ru.grammar.punct.comma` | придаточное: «Я знаю, что …» |

**Intent routing:** `semantic_read` → `grammar`; маркеры «запят», «верно ли», «проверь».

**Probe:** `probe_grammar_punct_ru` — минимальный held-out на comma + `что` (расширяемо).

**Отличие от орфографии:** punct = **структура предложения**; ortho = **графемы слова**. Оба через `ru.grammar.*` claims, разные `section`.

---

## Иерархия памяти (T0–T3) и fluency

```text
T0 grapheme     — алфавит (bootstrap, не цель диалога)
T1 syllable     — слог (analytic read, дети/ambiguous)
T2 lexicon      — lang.word.*  ← PRIMARY для fluency
T3 phrase       — events, slots (ADR-0033)
```

**Promote path:** grapheme/syllable success **не** auto-promote в whole-word без **отдельного** lexical gate.

---

## Категории РЯ (носитель) — канон curriculum

Четыре опоры выше — **target письменного fluency** (понимание + норма + dialog text). Школьные разделы — **каркас**, не лингвистический syllabus. Полная программа:

| Документ | Содержание |
|----------|------------|
| [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md) | оси A/B; владение vs теория; **модальность v1 = письменный**; B3 audio deferred |
| [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md) | фазы I–III; visual + text tract; waves 1–4 (audio = wave 4) |

**Сводка mapping (опоры → разделы B):**

```text
L1 whole-word  ←  A3 + B4 (lexicon)
L2 OOV         ←  A3 + B4
L3 orthography ←  B8 (+ B5 morphemics)
L4 punctuation ←  B9 (+ B7 syntax)
Dialogue       ←  B10 written (сквозной, ADR-0045)
Audio / B3     ←  deferred (не блокирует v1)
```

**Visual class сегодня:** `lessons/literacy-cards/class.manifest.json` — Phase I–II; Phase III (text/speech tract) — planned в class-ru-v1.

---

## KB + field (два слоя, один bind)

| Слой | Роль |
|------|------|
| **KB bundle** | transport: `ru.dialog.*`, `ru.grammar.*`, `lang.word.*` для orient |
| **Field + journal** | mastery: confirmed hypotheses, whole-word votes |
| **Dialogue** | bind KB + journal; **field-mastery-first** над transport-only glyph/math |

**Canonical bundle (v0):** `lab/kb-bundles/kb-lang-ru-grammar-dialog-v1.bundle.json`  
Runtime: `agents/von-neumann/bundles/`  
Lesson: `lessons/lang-ru-grammar-dialog/README.md`

---

## Skills и routing (ADR-0035)

| skill id | Тракт | Gate |
|----------|-------|------|
| `skill.read.whole` | lexical fluent read | `probe_lexical_read_fluent_ru` |
| `skill.read.analytic` | syllable/grapheme fallback | existing R1 probe |
| `skill.spell.check` | ortho norm in context | `probe_orthography_ru` |
| `skill.punct.check` | punct norm in context | `probe_grammar_punct_ru` |
| `skill.lex.oov_remember` | OOV → remember → LTM | `probe_oov_word_recall_ru` |

**Capability router (target):**

```json
{
  "route_kind": "capability",
  "match": { "modality": "t9", "surface_class": "word", "novel": "false" },
  "target_skill": "skill.read.whole"
}
```

```json
{
  "route_kind": "capability",
  "match": { "modality": "t9", "surface_class": "word", "novel": "true" },
  "target_skill": "skill.lex.oov_remember"
}
```

---

## Тракты Teacher 1–5 (сводка)

| # | Тракт | Classify | Synthesize | Verify |
|---|--------|----------|------------|--------|
| F1 | **Lexical read** | known word | `predict_lex` / whole | fluent probe |
| F2 | **OOV word** | novel surface | remember + `lang.word.*` | recall cue |
| F3 | **Orthography** | spelling intent | grammar atom bind | held-out form |
| F4 | **Punctuation** | punct intent | comma rule atom | held-out sentence |
| F5 | **Dialogue social** | social | `ru.dialog.*` + journal | partner turn |

---

## Implementation ladder

| # | Задача | Статус |
|---|--------|--------|
| 1 | ADR-0049 (этот документ) | **done** |
| 1b | Категории B1–B10 + class program v1 | **done** — [categories-v0](CASA-ru-native-categories-v0.md), [class-ru-v1](CASA-von-neumann-class-ru-v1.md) |
| 2 | `kb-lang-ru-grammar-dialog-v1` bundle + lesson README | **draft** — lab + store copy |
| 3 | `semantic_read`: social/lang hints; KB boost | planned |
| 4 | `subject_dialogue_bind`: mastery-first; filter grapheme surprise on social | planned |
| 5 | `subject_articulation`: social/grammar from KB atoms | planned |
| 6 | Journal: confirmed `lang.word.привет` + social cues | planned |
| 7 | Probe `probe_lexical_read_fluent_ru` + promote `skill.read.whole` | planned |
| 8 | OOV smoke: one novel word → remember → recall | planned |
| 9 | `kb-lang-ru-orthography-v1` expand + punct/ortho probes | planned |
| 10 | Route known→whole / novel→OOV in capability_router | planned |

**Smoke (dialogue):** `tests/test_subject_dialogue.py`, `tests/test_semantic_read_kb_bind.py`  
**Smoke (fluency):** `tests/test_lexical_read_fluent_ru.py` (planned)  
**Smoke (OOV):** `tests/test_oov_word_remember.py` (planned)

---

## Non-goals

- **Лингвистика** / академическая грамматика как syllabus
- **Аудио** (устная речь, орфоэпия, диктант на слух) — до отдельного ADR/тракта
- LLM / cloud как «носительский» переводчик на hot path
- pymorphy / morph oracle на read path (ADR-0036)
- Syllable-first как **конечная** форма взрослого чтения
- Paste абзацев grammar KB в ответ
- ЕГЭ-шаблон «вставь запятую» без field bind
- Полный словарь Ожегова в bundle до emergent OOV tract

---

## Acceptance (nositel′ v0 — педагогический gate)

**Probe:** `lab/visual-curriculum/probe_nositel_acceptance_ru.py`  
**Plan:** `lessons/ru-text-tract/data/nositel-acceptance-plan.json`  
**Инвариант:** ответ = **compose** из slots/атомов поля (`phrase_compose`), не paste длинного claim; **без meta-хвоста** в user-facing; длина = bind (stance + score floor).

**Gate policy `strict_v2` (plan):** intent match; top-2 concept; no defer на teachable cues; no dev-jargon (`bind`, `paste claim`, `llm`…); explain = gloss (—), не greeting-only; social greeting ≤3 предложения; honesty = partial без выдумки.

| Dim | Сценарий | Критерий strict_v2 |
|-----|----------|-------------------|
| **self** | «Кто ты? Расскажи о себе» | top `ru.dialog.self`; ≥2 предл.; нейманн+поле; no jargon |
| **capabilities** | «Что ты умеешь?» | top `ru.dialog.capabilities`; умею+русск |
| **affect** | «Как ты себя чувствуешь?» | top `ru.dialog.affect`; честно не-человек |
| **explain** | «Объясни, что такое …» / норма | intent explain/grammar; gloss или norm; no defer |
| **social** | привет / спасибо | top dialog atom; кратко; no grapheme surprise |
| **grammar** | ortho/punct held-out | norm в ответе |
| **honesty** | вне домена KB | partial/defer, не галлюцинация |

**Не равно Phase III / fluent L1** — отдельные probes ниже.

**Сквозные (Phase III, отдельные probes):**

- **L1** Known word → `skill.read.whole`, не forced analytic (`probe_lexical_read_fluent_ru`).
- **L2** Novel word → remember + recall (`probe_oov_word_recall_ru`).

Старые 5 пунктов — подмножество; gate Блока 12 = **nositel acceptance plan** целиком.

---

## Открытые вопросы

1. Единый **`kb-lang-ru-literacy-v1`** (dialog + ortho + punct) vs отдельные bundles?
2. **Discourse read** (ADR-0043/0044): когда подключать S-layer к punct в длинном prose?
3. **EN parity** — отдельный ADR или зеркало `skill.read.whole` для `locale: en`?

---

## Ссылки

- Категории: [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md)
- Класс von-neumann: [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md)
- KE / KB: [CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md](CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md)
- Dialogue: [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md)
- Routing: [CASA-ADR-0035-multi-layer-routing.md](CASA-ADR-0035-multi-layer-routing.md)
- Bundle: `lab/kb-bundles/kb-lang-ru-grammar-dialog-v1.bundle.json`
- Code: `casa/prisms/tick/semantic_read.py`, `casa/domain/subject_dialogue_bind.py`, `casa/domain/subject_articulation.py`, `casa/prisms/visual/analytic_read.py`
