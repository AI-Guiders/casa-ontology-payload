# Класс словесности (literacy-cards) — v1

**Статус:** черновик curriculum + lab (пилот RU OK)  
**Дорожная карта RU+EN:** [CASA-literacy-roadmap-v1.md](CASA-literacy-roadmap-v1.md)  
**Связано:** [CASA-ADR-0028](CASA-ADR-0028-field-native-sensory-experience.md), [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md)

## Идея

Тот же сюжет, что vis↔math, но **vis↔grapheme** на `alphabet-ru`:

| Кадр | Эпизод рядом (не на JPEG) |
|------|---------------------------|
| начертание **а** | `cue: a`, `register: lower`, surface `а` |
| начертание **А** | `cue: a`, `register: upper`, surface `А` |

Позже **stage-02**: те же `cue` + `register`, другой `face` (sans / serif / …) — отдельные `frame_id`, общий `concept_id` или связь через sleep.

## Инварианты

- **Без OCR на read path** — probe только поле + emergent `E:vis.lum.frame.*|co_occurs|grapheme.*`.
- **Один vis + один lexical на moment** — один sleep (как micro-geom); не пачковать много букв в один batch (cartesian S3b).
- **register** в `concept_id`: `grapheme.cyrl.{cue}.{register}` (например `grapheme.cyrl.a.lower`).

## Целостное слово (не «собрать из букв» на read)

Люди **не читают** обычный текст как последовательность «буква → слог → слово» в runtime. Слово воспринимается **цельным знаком** (форма строки, ритм, узнаваемый силуэт), как фигура «круг», а не как набор штрихов.

Для CASA это значит:

| Слой curriculum | Роль | На predict |
|-----------------|------|------------|
| **Слово** (`lang.word.*`, кадр целиком) | основной путь чтения | vis.whole_word → слово **одним** мостом |
| **Буква** (`grapheme.*`) | алфавит, регистр, новый шрифт, редкие формы | не обязательный разбор слова |
| **Слог** (`syllable.*`) | опционально для урока/языка, не цепочка декодера | не pipeline «сначала слоги» |

Буквы и слоги — **уроки учителя**, чтобы поле научилось **инвариантам** (шрифт, регистр, похожие черты), как контраст круг/квадрат. Это не инструкция агенту «раскладывай слово по частям», когда видишь «мама».

Аналогия с vis↔math: на квизе по слову probe спрашивает **какой lexical смысл на поле**, не «назови буквы по порядку».

**Вердикт probe:** единственный лидер по score = hint → **знаю**; несколько concept на max score → **не знаю** (ambiguous), не ошибка; единственный лидер ≠ hint → miss (учитель меняет подачу). См. `lab/visual-curriculum/probe_lex_verdict.py`, протокол vis↔math.

## Фазы (порядок смысла, не декодер)

1. **lesson-01-letters-cyrl** — изолированные буквы (фон алфавита, регистр).
2. **lesson-02-letters-faces** — те же буквы, другие начертания.
3. **lesson-03-words-cyrl** — **цельные** короткие слова (мама, кот, …), один кадр = одно слово; lexical cue = слово целиком.
4. **lesson-04-words-faces** — те же слова, другие шрифты (перенос целостности, не переспеллинг).
5. **Слоги** (если нужны педагогически) — отдельные кадры-слоги **без** требования пройти их перед словами на read path; возможны параллельно или после первых цельных слов.

Порядок уроков в классе ≠ алгоритм чтения. Сначала можно дать и слова, и буквы разными moment’ами; что «всплывёт» на held-out слове — диагностика, не сборка по слогам.

## Метаязык отдельно (канон, lab 2026-06-03)

**Цель:** речь учителя опирается на **уже ученые** `lang.word.*`, не на OCR с JPEG и не на смешение меты с grapheme в одном sleep.

**Главный вывод:** мета-слова нужно давать **отдельными** moment’ами — как vis↔math «один смысл за sleep», иначе поле склеивает фразу, букву и категорию (probe **ambiguous**).

| Слой | Moment | Read path |
|------|--------|-----------|
| **Мета на карточке-фразе** | `lex_only` или `phrase_vis` (1 vis + 1 lex), **без** `letter-*` | probe по `word-*-sans` → **know** на `lang.word.*` (проверено: `capital_letter`, `ne_znayu`) |
| **Grapheme / регистр** | `letter-{cue}-{register}` + lexical `grapheme.*` | probe по букве → `grapheme.*` (контрасты Б/В, upper-only, …) |
| **Категория регистра** | фразы — **pure**; exemplar буквы — **отдельно**, cue **не a** сначала | на букве категория часто **ambiguous** рядом с grapheme — ожидаемо до guided |
| **«Не знаю» состояние** | уровень 2: guided после ambiguous | **не** то же, что карточка `ne_znayu` (уровень 1) |

| Ступень | Содержание |
|--------|------------|
| **Метаязык w1** | `буква`, `слово`, `заглавная`, `строчная` |
| **Метаязык w2** | эпистемика/грамматика (legacy `lang.word.*` → `lang.meta.*`); **размер:** `lang.meta.size.large` / `.small` |
| **Кадры** | отдельное слово на JPEG → `lang.word.*` на `lexicon-ru` |
| **Чистый meta-moment** | только episodic и/или `phrase_vis` на **своём** frame_id |
| **Guided moment (осторожно)** | vis + мета + grapheme в **одном** sleep — **не** единственный путь меты; для а/А давал шум |

**Не смешивать:** `lang.word.zaglavnaya` ↔ `grapheme.cyrl.a.upper` (прилагательное ↔ одна буква).

**Размер на геометрии (идея):** `большая` / `маленкая` из w2 дублировать визуально на `visual-cards` — большой круг vs маленький круг, **чистые** moment’ы (мета отдельно от `geom.circle` и т.п.). См. [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) § Vis↔lex.

**Категория регистра** — два имени одного инварианта, exemplar vis **без** `grapheme.*` в том же moment:

| Инвариант | Имена (`lang.word.*`) | Exemplar (vis) |
|-----------|------------------------|----------------|
| верхний регистр | `lang.word.capital_letter` — surfaces «заглавная буква», «буква верхнего регистра» | exemplar `letter-{cue}-upper-sans` (**Б, В**, …; **а** — отдельно) |
| нижний регистр | `lang.word.lowercase_letter` — surfaces «строчная буква», «буква нижнего регистра» | exemplar `letter-{cue}-lower-sans` (**б, в**, …) |

**Контраст заглавных** (grapheme, без категории в том же moment): `run_upper_register_contrast.py` — чередование `letter-b-upper`, `letter-v-upper`, …

**Именование:** см. протокол § Семантическое именование. Канон регистра: `lang.meta.letterCase.upper` / `.lower`. В store могут быть legacy `lang.word.capital_letter` — на predict они **сливаются** в канон (алиасы, тот же `lexicon-ru`).

```json
[
  {"visual_frame": "letter-a-upper-sans"},
  {"lexical": {"concept_id": "lang.word.capital_letter", "correct": "заглавная буква"}},
  {"lexical": {"concept_id": "lang.word.capital_letter", "correct": "буква верхнего регистра"}}
]
```

`grapheme.cyrl.a.upper` — отдельный алфавитный урок (экземпляр), не мост «заглавная»→«А».

Слух (`auditory`) — усилитель позже; для v1 достаточно **symbolic afferent** (ADR-0028).

**Lab (порядок смысла):**

1. `build_register_phrase_cards.py`
2. **`run_register_category_pure.py`** — мета категории **сначала**
3. `run_upper_register_contrast.py` → `run_register_category.py --exemplar-cues b v --names-rounds 0`
4. **`run_meta_ne_znayu_pure.py`** — «не знаю» уровень 1 (карточка)

## Lab

```text
lessons/literacy-cards/
  class.manifest.json
  lesson-01-letters-cyrl/     # буквы
  lesson-07-meta-language/    # мета-фразы на JPEG
  lesson-03-words-cyrl/       # слова целиком → lang.word.* на lexicon-ru
  tools/build_letter_cards.py
  tools/build_word_cards.py
  tools/build_meta_language_cards.py
  tools/build_register_phrase_cards.py
lab/visual-curriculum/
  README.md
  curriculum_lab.py            # CurriculumLabSession (все lesson-классы)
  lex_steps.py                 # lex_step (vis↔lex, общий)
micro-literacy/
  literacy_steps.py            # re-export lex_step (совместимость)
  run_register_category_pure.py
  run_meta_ne_znayu_pure.py
  run_upper_register_contrast.py
  run_register_category.py
  run_meta_language_pilot.py
  run_meta_language_wave2.py
  probe_grapheme_quiz.py
  probe_lex_verdict.py
```
